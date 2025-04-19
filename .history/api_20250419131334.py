from fastapi import FastAPI, HTTPException, Request
import uvicorn
from pydantic import BaseModel
import json
from typing import Optional, Dict, Any, List

from transform_xhs import extract_xhs_content

app = FastAPI()

class XHSRequest(BaseModel):
    url: str

class XHSResponse(BaseModel):
    title: str
    description: str
    type: str
    images: List[Dict[str, Any]]
    original_url: str

@app.post("/extract", response_model=Dict[str, Any])
def extract_content(request: XHSRequest):
    """
    Extract content from a Xiaohongshu URL.
    Returns title, description, images, and other metadata.
    """
    result = extract_xhs_content(request.url)
    
    if not result or "error" in result:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to extract content"))
    
    # Process the result to remove binary content that can't be serialized to JSON
    if "images" in result and result["images"]:
        for image in result["images"]:
            # Remove binary content from response
            if "content" in image:
                del image["content"]
    
    return result

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 