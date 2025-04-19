import requests
import os
import logging
from typing import List, Dict, Any
import base64
from pathlib import Path

LOGGER = logging.getLogger(__name__)

def download_image(url: str) -> bytes:
    """Download image from URL and return its binary content"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
        LOGGER.error(f"Error downloading image from {url}: {e}")
        return None

def encode_image_base64(image_content: bytes) -> str:
    """Encode image to base64 for embedding in notes"""
    if not image_content:
        return None
    try:
        return base64.b64encode(image_content).decode('utf-8')
    except UnicodeDecodeError as e:
        LOGGER.error(f"Error encoding image to base64: {e}")
        return None

def process_image_urls(image_urls: List[str]) -> List[Dict[str, Any]]:
    """Process list of image URLs, download and encode them for embedding in notes"""
    processed_images = []
    
    for url in image_urls:
        LOGGER.info(f"Processing image: {url}")
        image_content = download_image(url)
        if image_content:
            # Get the file extension from URL
            ext = os.path.splitext(url.split('?')[0])[1] or '.jpg'
            base64_str = encode_image_base64(image_content)
            
            # Only add images that were successfully encoded
            if base64_str:
                processed_images.append({
                    'url': url,
                    'content': image_content,  # This will be removed in the API response
                    'base64': base64_str,
                    'extension': ext
                })
            else:
                # Add the image without binary content if encoding failed
                processed_images.append({
                    'url': url,
                    'extension': ext
                })
    
    return processed_images 