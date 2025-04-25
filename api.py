from fastapi import FastAPI, HTTPException, Request, Depends
import uvicorn
from pydantic import BaseModel
import logging
from typing import Optional, Dict, Any
import os

# 导入自定义模块
from content_extractor import detect_content_type, extract_content
from notion_handler import create_notion_page, verify_database_structure

# 初始化日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 验证必要的环境变量
required_env_vars = [
    'FIRECRWL_API_KEY',
    'INSTAGRAM_USERNAME',
    'INSTAGRAM_PASSWORD',
    'NOTION_API_KEY',
    'NOTION_DATABASE_ID',
    'CLOUDINARY_CLOUD_NAME',
    'CLOUDINARY_API_KEY',
    'CLOUDINARY_API_SECRET'
]

for var in required_env_vars:
    if not os.getenv(var):
        logger.error(f"缺少必要的环境变量: {var}")
        raise ValueError(f"缺少必要的环境变量: {var}")

# 创建FastAPI实例
app = FastAPI(
    title="内容同步API",
    description="自动提取各平台内容并同步到Notion数据库",
    version="1.0.0"
)

# 请求模型定义
class ContentRequest(BaseModel):
    content: str
    database_id: str  # Notion数据库ID

# 响应模型定义
class ContentResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

@app.post("/process", response_model=ContentResponse)
async def process_content(request: ContentRequest):
    """
    处理内容并同步到Notion
    
    参数:
        request: 包含内容和Notion数据库ID的请求
    
    返回:
        处理结果
    """
    try:
        # 验证数据库结构
        verify_result = verify_database_structure(request.database_id)
        if not verify_result["success"]:
            return ContentResponse(
                success=False,
                message=f"Notion数据库结构不符合要求: {verify_result['message']}",
                data={"verify_result": verify_result}
            )
            
        # 检测内容类型
        content_info = detect_content_type(request.content)
        logger.info(f"内容类型: {content_info['type']}, 平台: {content_info.get('platform')}")
        
        # 提取内容
        extracted_data = extract_content(content_info)
        
        if not extracted_data["success"]:
            return ContentResponse(
                success=False,
                message=f"无法提取内容，可能是不支持的平台或链接无效",
                data=extracted_data
            )
        
        # 创建Notion页面
        notion_result = create_notion_page(request.database_id, extracted_data)
        
        if not notion_result["success"]:
            return ContentResponse(
                success=False,
                message=f"无法创建Notion页面: {notion_result.get('message', '未知错误')}",
                data=extracted_data
            )
        
        return ContentResponse(
            success=True,
            message="成功处理内容并同步到Notion",
            data={
                "extracted_data": extracted_data,
                "notion_page_id": notion_result.get("page_id", "")
            }
        )
    
    except Exception as e:
        logger.error(f"处理内容时出错: {str(e)}")
        return ContentResponse(
            success=False,
            message=f"处理内容时出错: {str(e)}"
        )

@app.get("/health")
def health_check():
    """
    健康检查接口
    """
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 