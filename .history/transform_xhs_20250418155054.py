import requests
from typing import Optional
import logging
import re

from bs4 import BeautifulSoup

from .image_upload import process_image_urls

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def extract_url(pasted_text):
    url_pattern = r"(https?://[^，\s]+)"
    match = re.search(url_pattern, pasted_text)
    return match.group(1) if match else None


def get_final_url(short_url):
    try:
        response = requests.get(short_url, allow_redirects=True)
        response.raise_for_status()
        return response.url
    except requests.RequestException as e:
        LOGGER.error(f"An error occurred: {e}")
        return None


def extract_xhs_content(pasted_text: str) -> Optional[str]:
    """提取小红书内容"""
    try:
        short_url = extract_url(pasted_text)
        if not short_url:
            return {"error": "Failed to extract URL from pasted text"}

        # 提取完整 URL
        final_url = get_final_url(short_url)
        if not final_url:
            return {"error": "Failed to get the final URL"}

        response = requests.get(final_url)
        soup = BeautifulSoup(response.text, "html.parser")

        is_video = bool(soup.find("div", class_=["player-el"]))
        LOGGER.info(f"Is video: {is_video}")
        image_tags = soup.find_all("meta", attrs={"name": "og:image"})
        image_urls = [tag["content"] for tag in image_tags if "content" in tag.attrs]


        # 尝试获取标题和描述
        title_tag = soup.find("meta", attrs={"name": "og:title"})
        title = title_tag["content"] if title_tag and "content" in title_tag.attrs else ""

        description_tag = soup.find("meta", attrs={"name": "description"})
        description = description_tag["content"] if description_tag and "content" in description_tag.attrs else ""

        # 组合内容
        # content = f"{title}\n{description}".strip()
        # return content if content else None
        return {"type": "视频" if is_video else "图文", "title": title, "images": image_urls, "description": description}
    
    except Exception as e:
        LOGGER.error(f"Error extracting XHS content: {e}")
        return None
