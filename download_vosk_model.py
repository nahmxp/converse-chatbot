#!/usr/bin/env python3
"""
Script to download Vosk speech recognition model
"""
import os
import urllib.request
import zipfile
import sys

def download_model():
    model_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    model_zip = "vosk-model-small-en-us-0.15.zip"
    model_dir = "vosk-model-small-en-us-0.15"
    
    if os.path.exists(model_dir):
        print(f"Model {model_dir} already exists!")
        return True
    
    print("Downloading Vosk model (about 40MB)...")
    try:
        urllib.request.urlretrieve(model_url, model_zip)
        print("Download complete. Extracting...")
        
        with zipfile.ZipFile(model_zip, 'r') as zip_ref:
            zip_ref.extractall(".")
        
        os.remove(model_zip)
        print(f"Model extracted to {model_dir}")
        return True
        
    except Exception as e:
        print(f"Error downloading model: {e}")
        return False

if __name__ == "__main__":
    success = download_model()
    if success:
        print("\nModel downloaded successfully!")
        print("You can now use voice input in the chatbot.")
    else:
        print("\nFailed to download model.")
        sys.exit(1)
