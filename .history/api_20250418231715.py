from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends, Form, File, UploadFile
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import json
import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from transform_xhs import extract_xhs_content
from image_upload import download_image

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 创建保存图片的目录
SAVE_DIR = Path("./saved_content")
SAVE_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="小红书内容提取器API",
    description="提取小红书内容和图片的API，支持保存到本地文件或直接返回JSON数据。",
    version="1.0.0",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

# 模型定义
class XHSRequest(BaseModel):
    url: str = Field(..., description="小红书链接，可以是分享链接或完整链接")
    save_to_file: bool = Field(False, description="是否保存内容和图片到服务器文件")

class XHSResponse(BaseModel):
    title: str
    description: str
    type: str
    images: List[Dict[str, Any]]
    original_url: str
    saved_path: Optional[str] = None

# 后台任务：保存内容到文件
def save_content_to_file(content: Dict[str, Any]) -> str:
    """将抓取的内容保存到文件"""
    try:
        # 创建一个唯一的目录
        today = datetime.now().strftime("%Y%m%d")
        save_dir = SAVE_DIR / today
        save_dir.mkdir(exist_ok=True)
        
        # 创建一个基于标题的目录名（移除非法字符）
        title = content.get("title", "未命名")
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
        safe_title = safe_title[:50]  # 限制长度
        
        # 添加时间戳以确保唯一性
        timestamp = datetime.now().strftime("%H%M%S")
        dir_name = f"{timestamp}_{safe_title}"
        content_dir = save_dir / dir_name
        content_dir.mkdir(exist_ok=True)
        
        # 保存元数据到JSON
        meta_file = content_dir / "metadata.json"
        meta_content = {
            "title": content.get("title", ""),
            "description": content.get("description", ""),
            "type": content.get("type", ""),
            "original_url": content.get("original_url", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta_content, f, ensure_ascii=False, indent=2)
        
        # 保存图片
        images = content.get("images", [])
        for i, img in enumerate(images):
            if "content" in img and img["content"]:
                ext = img.get("extension", ".jpg")
                img_file = content_dir / f"image_{i+1}{ext}"
                with open(img_file, "wb") as f:
                    f.write(img["content"])
                # 记录本地保存路径而不是二进制内容
                img["local_path"] = str(img_file)
                # 移除二进制内容以减少JSON大小
                img.pop("content", None)
        
        # 保存完整内容
        full_content_file = content_dir / "full_content.json"
        with open(full_content_file, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
            
        return str(content_dir)
    except Exception as e:
        logger.error(f"保存内容时出错: {e}")
        return ""

@app.post("/extract", response_model=Dict[str, Any])
async def extract_content(request: XHSRequest, background_tasks: BackgroundTasks):
    """
    提取小红书内容并返回。
    
    - **url**: 小红书分享链接
    - **save_to_file**: 是否保存内容到服务器文件
    
    返回包含标题、描述、图片和原始URL的内容
    """
    try:
        result = extract_xhs_content(request.url)
        
        if not result or "error" in result:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to extract content"))
        
        # 如果需要保存到文件
        if request.save_to_file:
            saved_path = save_content_to_file(result)
            result["saved_path"] = saved_path
        
        return result
    except Exception as e:
        logger.error(f"提取内容出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器处理出错: {str(e)}")

@app.post("/extract_form")
async def extract_content_form(url: str = Form(...), save_to_file: bool = Form(False)):
    """通过表单提交的链接提取内容，适用于网页表单"""
    request = XHSRequest(url=url, save_to_file=save_to_file)
    return await extract_content(request, BackgroundTasks())

@app.get("/download/{date}/{dir_name}/image_{image_id}{ext}")
async def download_image_file(date: str, dir_name: str, image_id: int, ext: str):
    """获取保存的图片文件"""
    file_path = SAVE_DIR / date / dir_name / f"image_{image_id}{ext}"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="图片未找到")
    return FileResponse(file_path)

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """根接口，提供使用说明"""
    return {
        "message": "小红书内容提取器API",
        "usage": "POST /extract 使用JSON格式: {'url': '小红书链接', 'save_to_file': false}",
        "form_usage": "POST /extract_form 使用表单提交，参数: url, save_to_file",
        "docs": "/docs 查看API文档",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 