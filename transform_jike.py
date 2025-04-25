import requests
from typing import Optional
import logging

from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def extract_jike_content(url: str) -> Optional[str]:
    """提取即刻内容"""
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        # 找到包含文本的 div
        content_div = soup.find("div", class_="jsx-3930310120 wrap")
        if content_div:
            # 获取文本内容，保留换行符
            text = content_div.get_text(separator="\n", strip=True)
            LOGGER.info(f"Jike Content: {text}")
            return text
        return None
    except Exception as e:
        print(f"Error extracting Jike content: {e}")
        return None
