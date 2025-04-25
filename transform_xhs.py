import requests
from typing import Optional, Dict, Any, List, Tuple
import logging
import re
import urllib.parse
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Cloudinary配置
cloudinary.config( 
    cloud_name = "dumwcxeui", 
    api_key = "712717216572355", 
    api_secret = "-sqH9W4PuUIii2L1yctPCqFitKU",  # 请替换为你的API secret
    secure = True
)

# 定义函数，提取小红书链接
def extract_url(pasted_text):
    # 定义正则表达式，提取小红书链接
    url_pattern = r"(https?://[^，\s]+)"
    # 使用正则表达式提取小红书链接
    match = re.search(url_pattern, pasted_text)
    # 返回提取的小红书链接
    return match.group(1) if match else None

# 定义函数，获取最终的URL
def get_final_url(short_url):
    try:
        # 发送请求，获取最终的URL
        response = requests.get(short_url, allow_redirects=True)
        # 如果请求成功，返回最终的URL
        response.raise_for_status()
        return response.url
    except requests.RequestException as e:
        # 如果请求失败，返回None
        LOGGER.error(f"An error occurred: {e}")
        return None

def download_and_encode_image(url: str, max_size: int = 400, quality: int = 40) -> Optional[str]:
    """
    尝试下载图片，如果成功则返回原始URL
    
    参数:
        url: 图片URL
        max_size: 图片的最大尺寸（宽度或高度）- 已不再使用
        quality: JPEG压缩质量（1-100）- 已不再使用
        
    返回:
        成功时返回原始URL，失败时也返回原始URL并记录错误
    """
    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
            "Referer": "https://www.xiaohongshu.com/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
        }

        # 添加重试机制
        max_retries = 1
        for attempt in range(max_retries):
            try:
                LOGGER.info(f"测试图片URL是否可访问: {url}")
                response = requests.head(url, headers=headers, timeout=5)
                response.raise_for_status()
                LOGGER.info(f"图片URL可以访问: {url}")
                return url
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403 and attempt < max_retries - 1:
                    LOGGER.warning(f"尝试 {attempt+1}/{max_retries} 失败 (403 Forbidden)，重试中...")
                    continue
                LOGGER.error(f"HTTP错误: {e}")
                return url
            except Exception as e:
                LOGGER.error(f"请求错误: {e}")
                return url
        else:
            LOGGER.error(f"在 {max_retries} 次尝试后仍无法访问图片URL")
            return url
        
    except Exception as e:
        LOGGER.error(f"检查图片URL时出错: {str(e)}")
        # 返回原始URL
        return url

def upload_to_cloudinary(url: str) -> str:
    """
    将图片上传到Cloudinary
    
    参数:
        url: 原始图片URL
    
    返回:
        Cloudinary的图片URL
    """
    try:
        # 上传图片到Cloudinary
        upload_result = cloudinary.uploader.upload(
            url,
            folder="notion_images",  # 在Cloudinary中创建专门的文件夹
            transformation={
                'quality': 'auto',
                'fetch_format': 'auto'
            }
        )
        LOGGER.info(f"图片上传到Cloudinary成功: {upload_result['secure_url']}")
        return upload_result['secure_url']
    except Exception as e:
        LOGGER.error(f"上传图片到Cloudinary失败: {str(e)}")
        return url

def process_xhs_image_url(url: str) -> Tuple[str, List[str]]:
    """
    处理小红书图片URL
    
    参数:
        url: 原始图片URL
    
    返回:
        (处理后的图片URL, 空列表)
    """
    try:
        LOGGER.info(f"处理小红书图片URL: {url}")
        
        # 检查URL是否为空
        if not url:
            return "", []
        
        # 确保URL是HTTPS
        if url.startswith("http://"):
            url = "https://" + url[7:]
            
        # 上传到Cloudinary
        cloudinary_url = upload_to_cloudinary(url)
        LOGGER.info(f"使用Cloudinary URL: {cloudinary_url}")
        
        return cloudinary_url, []
    
    except Exception as e:
        LOGGER.error(f"处理小红书图片URL时出错: {str(e)}")
        return url, []

# 定义函数，提取小红书内容
def extract_xhs_content(pasted_text: str) -> Optional[Dict[str, Any]]:
    """提取小红书内容"""
    try:
        # 提取小红书链接
        short_url = extract_url(pasted_text)
        # 如果提取失败，返回错误信息
        if not short_url:
            return {"error": "Failed to extract URL from pasted text"}

        # 提取完整 URL
        final_url = get_final_url(short_url)
        if not final_url:
            return {"error": "Failed to get the final URL"}

        # 设置请求头，模拟浏览器访问
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.xiaohongshu.com/",
        }
        
        response = requests.get(final_url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        # 判断是否为视频
        is_video = bool(soup.find("div", class_=["player-el"]))
        LOGGER.info(f"Is video: {is_video}")
        
        # 收集所有图片URL
        image_tags = soup.find_all("meta", attrs={"name": "og:image"})
        # 提取图片URL
        raw_image_urls = [tag["content"] for tag in image_tags if "content" in tag.attrs]
        LOGGER.info(f"找到 {len(raw_image_urls)} 张图片")
        
        # 处理图片URL，验证其可访问性
        processed_image_urls = []
        
        for i, img_url in enumerate(raw_image_urls):
            # 处理图片URL
            processed_url, _ = process_xhs_image_url(img_url)
            if processed_url:
                LOGGER.info(f"处理第 {i+1} 张图片完成: {processed_url[:30]}...")
                processed_image_urls.append(processed_url)
        
        # 尝试获取标题和描述
        title_tag = soup.find("meta", attrs={"name": "og:title"})
        # 提取标题
        title = title_tag["content"] if title_tag and "content" in title_tag.attrs else ""
        # 提取描述
        description_tag = soup.find("meta", attrs={"name": "description"})
        description = description_tag["content"] if description_tag and "content" in description_tag.attrs else ""

        # 组合内容
        return {
            "type": "视频" if is_video else "图文", 
            "title": title, 
            "images": processed_image_urls,
            "content": description,
            "description": description,
            "source": "小红书",
            "original_url": final_url
        }
    
    except Exception as e:
        LOGGER.error(f"提取小红书内容时出错: {e}")
        return {"error": f"提取小红书内容时出错: {e}"}
