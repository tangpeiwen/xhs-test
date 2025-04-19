from fastapi import FastAPI, HTTPException, Request
import uvicorn
from pydantic import BaseModel
import json
import socket
from typing import Optional, Dict, Any, List

from transform_xhs import extract_xhs_content

app = FastAPI(title="Xiaohongshu Content Extractor")

class XHSRequest(BaseModel):
    url: str

class XHSResponse(BaseModel):
    title: str
    description: str
    type: str
    images: List[Dict[str, Any]]
    original_url: str

@app.post("/extract", response_model=Dict[str, Any])
async def extract_content(request: XHSRequest):
    """
    Extract content from a Xiaohongshu URL.
    Returns title, description, images, and other metadata.
    """
    result = extract_xhs_content(request.url)
    
    if not result or "error" in result:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to extract content"))
    
    return result

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/ip")
async def get_ip():
    """Return the local IP address for configuring Shortcuts"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    
    return {
        "ip": ip,
        "shortcuts_url": f"http://{ip}:8000/extract"
    }

@app.get("/")
async def root():
    """Root endpoint with usage instructions"""
    return {
        "message": "Xiaohongshu Content Extractor API",
        "usage": "POST /extract with JSON body: {'url': 'xiaohongshu-url'}",
        "ip_config": "GET /ip to get your local IP for Shortcuts configuration"
    }

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8000
    print(f"Starting server on all interfaces (0.0.0.0:{port})")
    print(f"To configure Shortcuts, visit: http://localhost:{port}/ip")
    uvicorn.run("api:app", host=host, port=port, reload=True) 