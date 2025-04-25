import logging
from typing import Optional, Dict, Any
import re
import os
import dotenv
import requests

dotenv.load_dotenv()

# 设置日志
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

class WebScraper:
    def __init__(self, api_key: str):
        """
        初始化 WebScraper
        :param api_key: Firecrawl API 密钥
        """
        self.api_key = api_key
        self.base_url = "https://api.firecrawl.dev/v1/scrape"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def extract_url(self, text: str) -> Optional[str]:
        """
        从文本中提取 URL
        :param text: 包含 URL 的文本
        :return: 提取出的 URL，如果没有找到则返回 None
        """
        url_pattern = r"(https?://[^\s]+)"
        match = re.search(url_pattern, text)
        return match.group(1) if match else None

    def scrape_content(self, url: str) -> Dict[str, Any]:
        """
        抓取网页内容
        :param url: 要抓取的网页 URL
        :return: 包含网页内容的字典
        """
        LOGGER.info(f"开始抓取网页内容: {url}")
        try:
            # 准备请求数据
            payload = {
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": True,
                "blockAds": True,
                "timeout": 30000
            }

            # 发送 POST 请求
            response = requests.post(
                self.base_url,
                json=payload,
                headers=self.headers
            )
            
            # 确保请求成功
            response.raise_for_status()
            
            # 直接返回 API 响应
            return response.json()

        except Exception as e:
            LOGGER.error(f"抓取内容时发生错误: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_title(self, markdown_content: str) -> str:
        """
        从 markdown 内容中提取标题
        :param markdown_content: markdown 格式的内容
        :return: 提取的标题
        """
        # 查找第一个 # 开头的行作为标题
        lines = markdown_content.split('\n')
        for line in lines:
            if line.strip().startswith('#'):
                return line.strip('#').strip()
            
        # 如果没有找到 # 开头的标题，返回空字符串
        return ""

def main():
    """
    主函数，演示如何使用 WebScraper
    """
    # 获取 API 密钥
    API_KEY = os.getenv("FIRECRWL_API_KEY")
    
    # 创建 WebScraper 实例
    scraper = WebScraper(API_KEY)
    
    # 示例：抓取网页内容
    url = input("请输入要抓取的网页 URL: ")
    result = scraper.scrape_content(url)
    
    if result.get("success"):
        data = result["data"]
        metadata = data.get("metadata", {})
        print("\n标题:", metadata.get("title", ""))
    else:
        print(f"\n抓取失败: {result.get('error', '未知错误')}")

if __name__ == "__main__":
    main() 