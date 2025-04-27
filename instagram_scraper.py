import os
import logging
import re
import urllib.parse
from typing import Dict, Any, List, Optional, Union
import dotenv
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, SelectContactPointRecoveryForm
from instagrapi.mixins.challenge import ChallengeChoice
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import json
import time
import imaplib
import email

dotenv.load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Cloudinary配置
cloudinary.config( 
    cloud_name = "dumwcxeui", 
    api_key = "712717216572355", 
    api_secret = "-sqH9W4PuUIii2L1yctPCqFitKU",
    secure = True
)

class CustomChallenge:
    def __init__(self, username: str, email: str):
        self.username = username
        self.email = email
        self.challenge_email = os.getenv("CHALLENGE_EMAIL")
        self.challenge_password = os.getenv("CHALLENGE_PASSWORD")
        
    def challenge_code_handler(self, username: str, choice: ChallengeChoice) -> str:
        """处理验证码请求"""
        if choice == ChallengeChoice.EMAIL:
            logger.info(f"Instagram请求邮箱验证码 - 用户: {username}")
            verification_code = self.get_verification_code()
            if verification_code:
                return verification_code
        return ""
        
    def get_verification_code(self) -> Optional[str]:
        """从邮箱获取Instagram验证码"""
        try:
            code = self.get_code_from_email(self.username)
            if code:
                logger.info("成功获取验证码")
                return code
            logger.warning("未找到验证码")
            return None
        except Exception as e:
            logger.error(f"获取验证码失败: {str(e)}")
            return None

    def get_code_from_email(self, username: str) -> Optional[str]:
        """从Gmail邮箱中获取Instagram验证码"""
        try:
            # 连接Gmail
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.challenge_email, self.challenge_password)
            mail.select("inbox")

            # 搜索未读邮件
            result, data = mail.search(None, "(UNSEEN)")
            if result != "OK":
                logger.error(f"搜索邮件失败: {result}")
                return None

            email_ids = data[0].split()
            if not email_ids:
                logger.warning("没有找到未读邮件")
                return None

            # 遍历未读邮件
            for num in reversed(email_ids):
                # 标记为已读
                mail.store(num, "+FLAGS", "\\Seen")
                
                # 获取邮件内容
                result, data = mail.fetch(num, "(RFC822)")
                if result != "OK":
                    continue

                email_body = data[0][1]
                email_message = email.message_from_bytes(email_body)

                # 处理邮件内容
                code = self._extract_code_from_email(email_message, username)
                if code:
                    return code

            return None

        except Exception as e:
            logger.error(f"处理邮件时出错: {str(e)}")
            return None
        finally:
            try:
                mail.close()
                mail.logout()
            except:
                pass

    def _extract_code_from_email(self, email_message: email.message.Message, username: str) -> Optional[str]:
        """从邮件内容中提取验证码"""
        try:
            # 获取邮件内容
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/html":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = email_message.get_payload(decode=True).decode()

            # 检查是否包含HTML内容
            if "<div" not in body:
                return None

            # 查找包含用户名的部分
            username_match = re.search(f">([^>]*?({username})[^<]*?)<", body)
            if not username_match:
                return None

            # 提取6位数验证码
            code_match = re.search(r">(\d{6})<", body)
            if code_match:
                return code_match.group(1)

            return None

        except Exception as e:
            logger.error(f"提取验证码时出错: {str(e)}")
            return None

class InstagramScraper:
    def __init__(self, username: str = None, password: str = None, session_file: str = "instagram_session.json"):
        """
        初始化Instagram爬虫
        :param username: Instagram用户名，如果为None则从环境变量获取
        :param password: Instagram密码，如果为None则从环境变量获取
        :param session_file: 保存session的文件路径
        """
        self.username = username or os.getenv("INSTAGRAM_USERNAME")
        self.password = password or os.getenv("INSTAGRAM_PASSWORD")
        self.session_file = session_file
        self.client = Client()
        self.is_logged_in = False
        self._load_session()

    def _save_session(self):
        """保存session信息到文件"""
        try:
            session_data = self.client.get_settings()
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f)
            logger.info("Session已保存")
        except Exception as e:
            logger.error(f"保存session失败: {str(e)}")

    def _load_session(self):
        """从文件加载session信息"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    session_data = json.load(f)
                self.client.set_settings(session_data)
                self.client.login(self.username, self.password)
                self.is_logged_in = True
                logger.info("成功从文件加载session")
                return True
        except Exception as e:
            logger.warning(f"加载session失败，将尝试重新登录: {str(e)}")
        return False

    def login(self) -> bool:
        """
        登录Instagram
        :return: 是否登录成功
        """
        try:
            if not self.is_logged_in:
                logger.info(f"尝试登录Instagram，用户名: {self.username}")
                self.client.login(self.username, self.password)
                self.is_logged_in = True
                self._save_session()  # 登录成功后保存session
                logger.info("登录成功")
            return True
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            return False

    def upload_to_cloudinary(self, url: str) -> str:
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
                folder="notion_images",  # 使用notion_images文件夹
                transformation={
                    'quality': 'auto',
                    'fetch_format': 'auto'
                }
            )
            logger.info(f"图片上传到Cloudinary成功: {upload_result['secure_url']}")
            return upload_result['secure_url']
        except Exception as e:
            logger.error(f"上传图片到Cloudinary失败: {str(e)}")
            return url

    def extract_media_pk(self, url: str) -> Optional[str]:
        """
        从Instagram URL中提取媒体ID
        :param url: Instagram媒体URL
        :return: 媒体ID或None
        """
        try:
            return self.client.media_pk_from_url(url)
        except Exception as e:
            logger.error(f"无法从URL提取媒体ID: {str(e)}")
            return None

    def extract_url(self, text: str) -> Optional[str]:
        """
        从文本中提取Instagram URL
        :param text: 包含URL的文本
        :return: 提取的URL或None
        """
        url_pattern = r"(https?://(?:www\.)?instagram\.com/[^\s]+)"
        match = re.search(url_pattern, text)
        return match.group(1) if match else None

    def simplify_instagram_url(self, url: str) -> str:
        """
        简化Instagram图片URL以便在Notion中正确显示
        :param url: 原始Instagram图片URL
        :return: 简化后的URL
        """
        try:
            if not url:
                return ""
                
            # 转换为字符串
            url_str = str(url)
            
            # 尝试简化URL
            # 方法1: 移除URL参数，只保留基本图片路径
            parsed_url = urllib.parse.urlparse(url_str)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            
            # 如果URL包含Instagram的CDN域名，尝试保留必要的参数
            if "cdninstagram.com" in base_url:
                # 保留一些必要的参数，去除其他可能导致问题的参数
                query_params = urllib.parse.parse_qs(parsed_url.query)
                essential_params = ['se', 'stp']
                simplified_params = {k: v[0] for k, v in query_params.items() if k in essential_params}
                
                if simplified_params:
                    query_string = urllib.parse.urlencode(simplified_params)
                    return f"{base_url}?{query_string}"
                
            return base_url
            
        except Exception as e:
            logger.error(f"简化URL时出错: {str(e)}, 原始URL: {url}")
            # 返回原始URL
            return str(url)

    def get_media_info(self, url: str) -> Dict[str, Any]:
        """
        获取Instagram媒体信息
        :param url: Instagram媒体URL
        :return: 包含媒体信息的字典
        """
        try:
            if not self.is_logged_in and not self.login():
                return {"success": False, "error": "无法登录Instagram"}

            # 提取URL（如果传入的是包含URL的文本）
            extracted_url = self.extract_url(url) or url
            
            # 获取媒体ID
            media_pk = self.extract_media_pk(extracted_url)
            if not media_pk:
                return {"success": False, "error": "无法从URL提取媒体ID"}
            
            # 获取媒体信息
            media_info = self.client.media_info(media_pk).dict()
            
            # 提取所需信息
            media_type = media_info.get('media_type')  # 1: 照片, 2: 视频, 8: 相册
            caption = media_info.get('caption_text', '')
            username = media_info.get('user', {}).get('username', '')
            
            # 准备返回的字典
            result = {
                "success": True,
                "media_type": media_type,
                "content": caption,
                "username": username,
                "original_url": extracted_url,
                "images": []
            }
            
            # 根据媒体类型提取图片URL并上传到Cloudinary
            if media_type == 1:  # 单张照片
                try:
                    image_url = media_info.get('image_versions2', {}).get('candidates', [])[0].get('url')
                    if image_url:
                        # 上传到Cloudinary
                        cloudinary_url = self.upload_to_cloudinary(image_url)
                        logger.info(f"Cloudinary图片URL: {cloudinary_url}")
                        result["images"].append(cloudinary_url)
                except (IndexError, KeyError) as e:
                    logger.warning(f"无法获取图片URL: {str(e)}")
            
            elif media_type == 8:  # 相册
                try:
                    resources = media_info.get('resources', [])
                    logger.info(f"相册资源数量: {len(resources)}")
                    
                    for resource in resources:
                        thumbnail_url = resource.get('thumbnail_url')
                        if thumbnail_url:
                            # 上传到Cloudinary
                            cloudinary_url = self.upload_to_cloudinary(thumbnail_url)
                            logger.info(f"Cloudinary相册图片URL: {cloudinary_url}")
                            result["images"].append(cloudinary_url)
                except Exception as e:
                    logger.warning(f"无法获取相册图片URL: {str(e)}")
            
            # 记录提取的图片数量
            logger.info(f"成功处理 {len(result['images'])} 张图片")
            return result
            
        except LoginRequired:
            # 如果登录过期，尝试重新登录
            self.is_logged_in = False
            if self.login():
                return self.get_media_info(url)  # 重新尝试
            return {"success": False, "error": "登录凭证已过期，重新登录失败"}
            
        except Exception as e:
            logger.error(f"获取媒体信息时出错: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

def main():
    """
    主函数，演示如何使用InstagramScraper
    """
    # 从环境变量获取凭证，或者直接传递给构造函数
    scraper = InstagramScraper()
    
    # 获取Instagram帖子URL
    url = input("请输入Instagram帖子URL: ")
    result = scraper.get_media_info(url)
    
    if result.get("success"):
        print(f"\n用户名: {result['username']}")
        print(f"媒体类型: {result['media_type']} (1:照片, 2:视频, 8:相册)")
        print(f"内容: {result['content']}")
        print(f"\n图片URL列表 ({len(result['images'])}张):")
        for i, img in enumerate(result['images'], 1):
            print(f"{i}. {img}")
        
    else:
        print(f"\n获取失败: {result.get('error', '未知错误')}")

if __name__ == "__main__":
    main() 