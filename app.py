import PyPDF2
import re
import os
from typing import Dict, List
import streamlit as st
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to get API key from .env
DEFAULT_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# PDF path
PDF_PATH = "assets/links.pdf"

class LinkHandler:
    def __init__(self, pdf_path: str):
        self.categories: Dict[str, List[Dict]] = {}
        self.pdf_path = pdf_path
        self.raw_text = ""  # Store raw text for debugging
        self._load_links_from_pdf()
    
    def _load_links_from_pdf(self):
        """Extract links and categories from the PDF file"""
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF file not found at {self.pdf_path}")
        
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                self.raw_text = text  # Save for debugging
                self._parse_text(text)
        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")
    
    def _parse_text(self, text: str):
        """Parse the extracted text to build categories and links"""
        current_category = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check for category headers (emoji indicators)
            if any(line.startswith(emoji) for emoji in ["🛒", "🎓", "✈", "🎬", "💼", "🏥"]):
                current_category = line
                self.categories[current_category] = []
            elif current_category and line:
                # Parse link lines (number. title – url)
                match = re.match(r'(\d+)\. (.+) – (https?://\S+)', line)
                if match:
                    _, title, url = match.groups()
                    self.categories[current_category].append({
                        "title": title.strip(),
                        "url": url.strip()
                    })
    
    def get_links_by_category(self, category: str) -> List[Dict]:
        """Get all links in a specific category"""
        return self.categories.get(category, [])
    
    def search_links(self, query: str) -> List[Dict]:
        """Search links by title or category"""
        results = []
        query = query.lower()
        for category, links in self.categories.items():
            for link in links:
                if (query in link['title'].lower() or 
                    query in category.lower()):
                    results.append(link)
        return results
    
    def get_all_links(self) -> List[Dict]:
        """Get all links from all categories"""
        return [link for links in self.categories.values() for link in links]

# Function to extract text from PDF
@st.cache_data(show_spinner=False)
def extract_pdf_text(pdf_path):
    if not os.path.exists(pdf_path):
        return ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
    except Exception as e:
        return f"Error reading PDF: {e}"

# Function to call OpenRouter API
def call_openrouter_api(api_key, prompt, pdf_text):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Given the following PDF content, answer the user's question by extracting and listing relevant links from the text. Only return links that are relevant to the user's prompt."},
        {"role": "user", "content": f"PDF Content:\n{pdf_text}\n\nUser Prompt: {prompt}"}
    ]
    data = {
        "model": "openrouter/auto",
        "messages": messages,
        "max_tokens": 256  # Limit the response length to fit within free tier
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"

def filter_pdf_text(pdf_text, query):
    """
    Return only lines from the PDF that match the user's query (case-insensitive).
    If nothing matches, fall back to the first 500 characters.
    """
    lines = pdf_text.splitlines()
    query = query.lower()
    filtered = [line for line in lines if query in line.lower()]
    return "\n".join(filtered) if filtered else pdf_text[:500]

# --- Streamlit UI ---
st.set_page_config(page_title="PDF Chatbot", layout="centered")
st.title("PDF Chatbot (OpenRouter)")

# Load PDF text (cache for performance)
pdf_text = extract_pdf_text(PDF_PATH)

# API Key input (if not in .env, ask user)
if DEFAULT_API_KEY:
    api_key = DEFAULT_API_KEY
    st.info("Loaded OpenRouter API key from .env file.")
else:
    api_key = st.text_input("Enter your OpenRouter API Key", type="password")

# User prompt input
user_prompt = st.text_input("Ask a question about the links in the PDF:")

# Terminal-like progress box
progress_box = st.empty()

# Button to get answer
if st.button("Get Answer"):
    terminal_log = []
    def log(msg):
        terminal_log.append(msg)
        progress_box.code("\n".join(terminal_log), language="bash")

    if not api_key:
        st.error("Please provide your OpenRouter API key.")
    elif not user_prompt:
        st.error("Please enter a question.")
    elif not pdf_text or pdf_text.startswith("Error"):
        st.error("Could not read PDF file.")
    else:
        log("[1/4] Filtering PDF for relevant lines...")
        pdf_excerpt = filter_pdf_text(pdf_text, user_prompt)
        log(f"[2/4] Preparing API request (max_tokens=256)...")
        log(f"[3/4] Sending request to OpenRouter API...")
        with st.spinner("Querying LLM..."):
            answer = call_openrouter_api(api_key, user_prompt, pdf_excerpt)
        log("[4/4] Response received!")
        st.markdown("**Answer:**")
        st.write(answer)
        log("---\n" + answer)