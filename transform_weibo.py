import re
import logging
from typing import Optional

from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def extract_weibo_id(url: str) -> Optional[str]:
    """从微博URL中提取status ID"""
    try:
        LOGGER.info(f"Extracting Weibo ID from URL: {url}")
        # 使用正则表达式匹配两种可能的格式
        # 1. status/数字
        # 2. 用户ID/数字
        match = re.search(r"(?:status/|com/\d+/)(\d+)", url)
        if match:
            weibo_id = match.group(1)
            LOGGER.info(f"Successfully extracted Weibo ID: {weibo_id}")
            return weibo_id
        LOGGER.error(f"Could not find Weibo ID in URL: {url}")
        return None
    except Exception as e:
        LOGGER.error(f"Error extracting Weibo ID: {str(e)}")
        return None


def extract_text_from_html(html_string: str) -> str:
    """从HTML中提取纯文本，保留换行"""
    try:
        # 替换所有 <br> 标签为换行符
        html_string = re.sub(r"<br\s*/?>", "\n", html_string, flags=re.IGNORECASE)

        # 创建 BeautifulSoup 对象
        soup = BeautifulSoup(html_string, "html.parser")

        # 获取所有文本内容
        text = soup.get_text(separator=" ", strip=True)

        # 清理多余的空格，但保留换行
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(line for line in lines if line)

        return text
    except Exception as e:
        LOGGER.error(f"Error extracting text from HTML: {str(e)}")
        return html_string
