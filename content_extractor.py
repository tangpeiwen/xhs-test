import os
import re
import logging
from typing import Dict, Any, List, Optional
import dotenv

# 导入各平台提取内容的函数
from transform_xhs import extract_xhs_content
from transform_weibo import extract_weibo_content
from transform_jike import extract_jike_content
from instagram_scraper import InstagramScraper
from firecrawl_scraper import WebScraper

# 初始化日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 加载环境变量
dotenv.load_dotenv()

# 定义平台类型枚举
PLATFORM_TYPES = {
    "xhslink": "小红书",
    "xiaohongshu": "小红书",
    "xhs": "小红书",
    "weibo": "微博",
    "okjike": "即刻",
    "instagram": "Instagram",
    "http": "网页",
    "https": "网页"
}

def detect_content_type(content: str) -> Dict[str, Any]:
    """
    检测内容类型：链接或纯文本
    如果是链接，识别来源平台
    
    参数:
        content: 用户输入的内容
    
    返回:
        内容类型信息字典
    """
    # 提取URL的正则表达式
    url_pattern = r"(https?://[^\s]+)"
    match = re.search(url_pattern, content)
    
    if not match:
        return {
            "type": "text",
            "platform": None,
            "content": content
        }
    
    url = match.group(1)
    # 识别平台
    platform = None
    for key, value in PLATFORM_TYPES.items():
        if key in url.lower():
            platform = value
            break
    
    # 如果没有匹配到特定平台但以http开头，标记为网页
    if not platform and (url.startswith("http://") or url.startswith("https://")):
        platform = "网页"
    
    return {
        "type": "url",
        "platform": platform,
        "url": url,
        "original_content": content
    }

def extract_content(content_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据内容类型和平台，提取相关内容
    
    参数:
        content_info: 内容类型信息字典
    
    返回:
        提取的内容信息
    """
    if content_info["type"] == "text":
        return {
            "success": True,
            "type": "text",
            "title": content_info["content"][:50] + ("..." if len(content_info["content"]) > 50 else ""),
            "content": content_info["content"],
            "source": "",  # 文本内容无来源，留空
            "tags": [],    # 文本内容无标签，设置为空列表
            "category": "文本"  # 改为单个字符串
        }
    
    platform = content_info["platform"]
    url = content_info["url"]
    logger.info(f"提取 {platform} 平台内容，URL: {url}")
    
    # 根据平台调用不同的提取函数
    if platform == "小红书":
        result = extract_xhs_content(url)
        if result and "error" not in result:
            return {
                "success": True,
                "type": "url",
                "title": result.get("title", ""),
                "content": result.get("description", ""),
                "images": result.get("images", []),
                "source": "小红书",
                "original_url": result.get("original_url", url),
                "tags": [],
                "category": "链接"  # 改为单个字符串
            }
    
    elif platform == "微博":
        content = extract_weibo_content(url)
        if content:
            return {
                "success": True,
                "type": "url",
                "title": content.split("\n")[0] if "\n" in content else content[:50],
                "content": content,
                "source": "微博",
                "original_url": url,
                "tags": [],
                "category": "链接"  # 改为单个字符串
            }
    
    elif platform == "即刻":
        content = extract_jike_content(url)
        if content:
            return {
                "success": True,
                "type": "url",
                "title": content.split("\n")[0] if "\n" in content else content[:50],
                "content": content,
                "source": "即刻",
                "original_url": url,
                "tags": [],
                "category": "链接"  # 改为单个字符串
            }
    
    elif platform == "Instagram":
        scraper = InstagramScraper()
        result = scraper.get_media_info(url)
        if result.get("success"):
            # 确保所有图片URL都是字符串
            images = []
            for img in result.get("images", []):
                if img is not None:
                    # 确保URL是字符串类型
                    images.append(str(img))
            
            return {
                "success": True,
                "type": "url",
                "title": f"{result.get('username', '')}的Instagram",
                "content": result.get("content", ""),
                "images": images,  # 使用处理后的图片列表
                "source": "Instagram",
                "original_url": str(result.get("original_url", url)),  # 确保original_url也是字符串
                "tags": [],
                "category": "链接"  # 改为单个字符串
            }
        else:
            logger.warning(f"Instagram内容提取失败: {result.get('error', '未知错误')}")
    
    elif platform == "网页":
        api_key = os.environ.get("FIRECRWL_API_KEY")
        if api_key:
            scraper = WebScraper(api_key)
            result = scraper.scrape_content(url)
            logger.info(f"网页内容提取结果: {result}")
            if result.get("success"):
                data = result.get("data", {})
                metadata = data.get("metadata", {})
                content = data.get("markdown", "")
                return {
                    "success": True,
                    "type": "url",
                    "title": metadata.get("title", ""),
                    "content": content,
                    "source": "",  # 普通网页内容无特定来源，留空
                    "original_url": url,
                    "tags": [],    # 网页内容可以不设标签，设置为空列表
                    "category": "链接"  # 改为单个字符串
                }
        else:
            logger.warning("未设置FIRECRWL_API_KEY，无法提取网页内容")
    
    # 如果没有成功提取或平台未识别
    logger.warning(f"未能成功提取内容，平台: {platform}")
    return {
        "success": False,
        "type": "url",
        "title": "",
        "content": url,
        "source": platform or "",  # 未识别平台可留空
        "original_url": url,
        "tags": [],  # 未识别内容不设标签
        "category": "链接"  # 改为单个字符串
    } 