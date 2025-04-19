from fastapi import FastAPI, HTTPException, Request
import uvicorn
from pydantic import BaseModel
import json
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

@app.get("/")
async def root():
    """Root endpoint with usage instructions"""
    return {
        "message": "Xiaohongshu Content Extractor API",
        "usage": "POST /extract with JSON body: {'url': 'xiaohongshu-url'}"
    }

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 