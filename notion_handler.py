import os
import logging
import re
import urllib.parse
import base64
import requests
from io import BytesIO
from typing import Dict, Any, List, Optional, Tuple
from notion_client import Client
import dotenv
from transform_xhs import process_xhs_image_url  # 导入从transform_xhs.py

# 初始化日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 加载环境变量
dotenv.load_dotenv()

# 获取Notion API密钥
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
if not NOTION_API_KEY:
    raise ValueError("NOTION_API_KEY 环境变量未设置")

# 初始化Notion客户端
notion = Client(auth=NOTION_API_KEY)

def create_notion_page(database_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    在Notion数据库中创建一个新页面
    
    参数:
        database_id: Notion数据库ID
        data: 包含页面内容的字典
    
    返回:
        结果字典，包含成功状态和消息
    """
    try:
        # 确保所有值都是JSON可序列化的
        sanitized_data = sanitize_data(data)
        
        # 检查是否是链接内容
        is_url = False
        original_url = sanitized_data.get("original_url", "")
        if original_url:
            # 检查是否是URL
            is_url = bool(re.match(r'https?://', original_url))
        
        # 准备Notion API所需的属性格式
        properties = {}
        
        # 处理Name字段
        if is_url:
            # 如果是链接，使用title作为Name
            title = sanitized_data.get("title", "")
            properties["Name"] = {
                "title": [
                    {
                        "text": {
                            "content": title if title else "Untitled"
                        }
                    }
                ]
            }
        else:
            # 如果是文本，使用content的缩略形式
            content = sanitized_data.get("content", "").strip()
            truncated_content = content[:20] + ("..." if len(content) > 20 else "") if content else "Untitled"
            properties["Name"] = {
                "title": [
                    {
                        "text": {
                            "content": truncated_content
                        }
                    }
                ]
            }
        
        # 处理Title/Content字段
        content = sanitized_data.get("content", "")
        if content:
            # 如果内容超过150个字符，只在Title/Content字段显示摘要
            content_preview = content[:150].strip()
            if len(content) > 150:
                content_preview += "..."
                
            properties["Title/Content"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": content_preview
                        }
                    }
                ]
            }
        else:
            properties["Title/Content"] = {
                "rich_text": []
            }
        
        # 处理URL字段
        if is_url:
            # 如果是小红书链接，使用short_url
            if "xiaohongshu.com" in original_url:
                short_url = original_url.split("?")[0]  # 移除查询参数
                properties["URL"] = {
                    "url": short_url
                }
            else:
                properties["URL"] = {
                    "url": original_url
                }
        else:
            properties["URL"] = {
                "url": None  # 如果不是链接，URL字段为空
            }
        
        # 添加Source字段（如果有来源）- 改为单选
        source = sanitized_data.get("source", "")
        if source:
            properties["Source"] = {
                "select": {
                    "name": source
                }
            }
        else:
            properties["Source"] = {
                "select": None
            }

        # 添加Category字段（改为单选）
        category = sanitized_data.get("category", "")
        if category:
            properties["Category"] = {
                "select": {
                    "name": category
                }
            }
        else:
            properties["Category"] = {
                "select": None
            }
        
        # Tag仍然保持为多选
        if "tags" in sanitized_data and sanitized_data["tags"] and isinstance(sanitized_data["tags"], list) and len(sanitized_data["tags"]) > 0:
            properties["Tag"] = {
                "multi_select": [
                    {"name": tag} for tag in sanitized_data.get("tags", [])
                ]
            }
        else:
            properties["Tag"] = {
                "multi_select": []
            }
        
        # 创建页面内容
        page_content = {
            "parent": {"database_id": database_id},
            "properties": properties,
        }
        
        # 准备页面内容块
        children = []
        
        # 如果有内容，添加到页面正文
        if "content" in sanitized_data and sanitized_data["content"]:
            # 添加一个标题
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "正文内容"
                            }
                        }
                    ]
                }
            })
            
            # 分段处理内容，避免超出Notion API限制
            content_chunks = split_content(sanitized_data["content"])
            
            for chunk in content_chunks:
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": chunk
                                }
                            }
                        ]
                    }
                })
        
        # # 记录原始URL
        # if "original_url" in sanitized_data and sanitized_data["original_url"]:
        #     children.append({
        #         "object": "block",
        #         "type": "paragraph",
        #         "paragraph": {
        #             "rich_text": [
        #                 {
        #                     "type": "text",
        #                     "text": {
        #                         "content": f"原始链接: {sanitized_data['original_url']}"
        #                     },
        #                     "annotations": {
        #                         "bold": True
        #                     }
        #                 }
        #             ]
        #         }
        #     })
        
        # 如果有图片，直接将图片作为图片块添加到页面
        if "images" in sanitized_data and sanitized_data["images"] and isinstance(sanitized_data["images"], list) and len(sanitized_data["images"]) > 0:
            # 添加一个分隔线
            children.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            
            # 添加图片标题
            children.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "图片内容"
                            }
                        }
                    ]
                }
            })
            
            # 收集所有备用URL
            all_backup_urls = []
            if "backup_images" in sanitized_data and sanitized_data["backup_images"]:
                all_backup_urls.extend(sanitized_data["backup_images"])
            
            # 添加每张图片作为图片块
            image_success_count = 0
            for img_url in sanitized_data["images"]:
                if not img_url:
                    continue
                    
                # 确保URL是字符串并且有效
                img_url_str = str(img_url)
                processed_url = img_url_str
                backup_urls = []
                
                # 根据URL来源进行特殊处理
                if "cdninstagram.com" in img_url_str:
                    processed_url = process_instagram_url(img_url_str)
                elif "xhscdn.com" in img_url_str or "xiaohongshu.com" in img_url_str:
                    processed_url, backup_urls = process_xhs_image_url(img_url_str)  # 使用从transform_xhs导入的函数
                    # 添加这张图片的备用URL到总备用URL列表
                    all_backup_urls.extend(backup_urls)
                
                logger.info(f"添加图片: {processed_url}")
                
                try:
                    # 尝试添加图片块
                    children.append({
                        "object": "block",
                        "type": "image",
                        "image": {
                            "type": "external",
                            "external": {
                                "url": processed_url
                            }
                        }
                    })
                    
                    # 添加图片链接作为文本备份
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"图片链接: {processed_url}",
                                        "link": {"url": processed_url}
                                    }
                                }
                            ]
                        }
                    })
                    
                    image_success_count += 1
                    
                except Exception as e:
                    logger.error(f"添加图片时出错: {str(e)}, URL: {processed_url}")
                    
                    # 如果添加图片失败，尝试使用备用URL
                    backup_success = False
                    
                    # 尝试使用当前图片的备用URL
                    for backup_url in backup_urls:
                        try:
                            logger.info(f"尝试使用备用URL: {backup_url}")
                            children.append({
                                "object": "block",
                                "type": "image",
                                "image": {
                                    "type": "file",
                                    "file": {
                                        "url": backup_url,
                                        "expiry_time": "2025-12-31T23:59:59Z"  # 设置一个较长的过期时间
                                    }
                                }
                            })
                            
                            # 添加备用图片链接作为文本备份
                            children.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": f"备用图片链接: {backup_url}"
                                            }
                                        }
                                    ]
                                }
                            })
                            
                            image_success_count += 1
                            backup_success = True
                            break
                        except Exception as e2:
                            logger.error(f"使用备用URL添加图片时出错: {str(e2)}, URL: {backup_url}")
                    
                    # 如果所有备用URL都失败，添加一个文本说明和链接
                    if not backup_success:
                        children.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": f"图片链接(无法嵌入): "
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": processed_url,
                                            "link": {"url": processed_url}
                                        }
                                    }
                                ]
                            }
                        })
            
            # 如果没有成功添加图片，添加备用说明
            if image_success_count == 0:
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "无法直接嵌入图片，请访问原始链接查看图片内容。"
                                },
                                "annotations": {
                                    "bold": True,
                                    "color": "red"
                                }
                            }
                        ]
                    }
                })
                
                # 添加原始图片链接作为文本
                if "raw_images" in sanitized_data and sanitized_data["raw_images"]:
                    for i, raw_url in enumerate(sanitized_data["raw_images"]):
                        if not raw_url:
                            continue
                            
                        children.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": f"原始图片 {i+1}: "
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": raw_url,
                                            "link": {"url": raw_url}
                                        }
                                    }
                                ]
                            }
                        })
                
                # 添加所有备用URL链接作为文本
                if all_backup_urls:
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "备用图片链接:"
                                    },
                                    "annotations": {
                                        "bold": True
                                    }
                                }
                            ]
                        }
                    })
                    
                    for i, backup_url in enumerate(all_backup_urls):
                        if not backup_url:
                            continue
                            
                        children.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": f"备用链接 {i+1}: "
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": backup_url,
                                            "link": {"url": backup_url}
                                        }
                                    }
                                ]
                            }
                        })
        
        # 如果有内容块，添加到页面内容中
        if children:
            page_content["children"] = children
        
        # 创建页面
        response = notion.pages.create(**page_content)
        logger.info(f"成功创建Notion页面: {response['id']}")
        
        return {
            "success": True,
            "message": "成功创建Notion页面",
            "page_id": response["id"]
        }
    
    except Exception as e:
        logger.error(f"创建Notion页面时出错: {str(e)}")
        return {
            "success": False,
            "message": f"创建Notion页面时出错: {str(e)}"
        }

def process_instagram_url(url: str) -> str:
    """
    处理Instagram图片URL，尝试多种方法使其在Notion中可显示
    
    参数:
        url: Instagram图片URL
    
    返回:
        处理后的URL
    """
    try:
        # 方法1: 移除查询参数，只保留基本URL
        parsed_url = urllib.parse.urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        
        # 如果URL包含特定的Instagram CDN
        if "cdninstagram.com" in url:
            # 方法2: 尝试只保留必要参数
            query_params = urllib.parse.parse_qs(parsed_url.query)
            essential_params = ['se', 'stp']
            simplified_params = {k: v[0] for k, v in query_params.items() if k in essential_params}
            
            if simplified_params:
                query_string = urllib.parse.urlencode(simplified_params)
                simplified_url = f"{base_url}?{query_string}"
                return simplified_url
        
        # 返回简化的URL
        return base_url
        
    except Exception as e:
        logger.error(f"处理Instagram URL时出错: {str(e)}")
        return url

def sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    确保所有数据都是JSON可序列化的
    
    参数:
        data: 原始数据字典
    
    返回:
        处理后的数据字典
    """
    result = {}
    for key, value in data.items():
        if key == "images" and isinstance(value, list):
            # 确保所有图片URL都是字符串
            result[key] = [str(img) for img in value if img is not None]
        elif key == "raw_images" and isinstance(value, list):
            # 保留原始图片URL
            result[key] = [str(img) for img in value if img is not None]
        elif isinstance(value, dict):
            result[key] = sanitize_data(value)
        elif isinstance(value, list):
            result[key] = [str(item) if not isinstance(item, (dict, list)) else item for item in value]
        else:
            # 确保所有值都是字符串
            result[key] = str(value) if value is not None else value
    return result

def clean_markdown_text(text: str) -> str:
    """
    清理 Markdown 文本，处理特殊字符和HTML标签
    
    参数:
        text: 原始文本
    
    返回:
        处理后的文本
    """
    # 替换HTML换行标签为实际换行
    text = text.replace("<br>", "\n")
    text = text.replace("<br/>", "\n")
    text = text.replace("<br />", "\n")
    
    # 处理转义字符
    text = text.replace("\\'", "'")
    text = text.replace('\\"', '"')
    text = text.replace("\\n", "\n")
    
    # 移除多余的换行
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()

def split_content(content: str, max_length: int = 1900) -> List[str]:
    """
    将长文本分割成适合Notion API的段落，使用更保守的长度限制
    
    参数:
        content: 要分割的内容
        max_length: 每段最大长度（默认1900，比Notion的2000限制更保守）
    
    返回:
        分割后的段落列表
    """
    logger.info(f"分割长度为 {len(content)} 的文本")
    chunks = []

    # 首先清理文本
    content = clean_markdown_text(content)
    
    # 按段落分割
    paragraphs = content.split("\n")
    current_chunk = []
    current_length = 0

    for paragraph in paragraphs:
        # 如果单个段落超过限制，需要进一步分割
        if len(paragraph) > max_length:
            logger.debug(f"发现长段落: {len(paragraph)} 字符")
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0

            # 分割长段落
            while paragraph:
                chunk = paragraph[:max_length]
                chunks.append(chunk)
                paragraph = paragraph[max_length:]
                logger.debug(f"创建长度为 {len(chunk)} 的块")
            continue

        # 检查添加新段落是否会超出限制
        if current_length + len(paragraph) + 1 > max_length:
            chunks.append("\n".join(current_chunk))
            current_chunk = [paragraph]
            current_length = len(paragraph)
        else:
            current_chunk.append(paragraph)
            current_length += len(paragraph) + 1  # +1 用于换行符

    # 添加最后一个块
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    # 验证所有块的长度并进行额外分割（如果需要）
    final_chunks = []
    for i, chunk in enumerate(chunks):
        if len(chunk) > 2000:
            logger.warning(f"块 {i} 太长: {len(chunk)} 字符，进行额外分割")
            # 进行额外的分割
            final_chunks.extend([chunk[j:j + 1900] for j in range(0, len(chunk), 1900)])
        else:
            final_chunks.append(chunk)

    logger.info(f"文本分割完成，共 {len(final_chunks)} 个块")
    return final_chunks

def get_notion_database_schema(database_id: str) -> Optional[Dict[str, Any]]:
    """
    获取Notion数据库的结构信息
    
    参数:
        database_id: Notion数据库ID
    
    返回:
        数据库结构信息，如果出错则返回None
    """
    try:
        database = notion.databases.retrieve(database_id=database_id)
        return database
    except Exception as e:
        logger.error(f"获取数据库结构时出错: {str(e)}")
        return None

def verify_database_structure(database_id: str) -> Dict[str, Any]:
    """
    验证Notion数据库结构是否符合要求
    
    参数:
        database_id: Notion数据库ID
    
    返回:
        验证结果
    """
    required_properties = {
        "Name": "title",
        "Title/Content": "rich_text",
        "Source": "select",     # 单选
        "Category": "select",   # 单选
        "Tag": "multi_select",  # 多选
        "URL": "url"           # 新增URL字段
    }
    
    try:
        database = get_notion_database_schema(database_id)
        if not database:
            return {
                "success": False,
                "message": "无法获取数据库信息"
            }
        
        properties = database.get("properties", {})
        missing_properties = []
        wrong_types = []
        
        for prop_name, prop_type in required_properties.items():
            if prop_name not in properties:
                missing_properties.append(prop_name)
            elif properties[prop_name]["type"] != prop_type:
                wrong_types.append(f"{prop_name} (应为 {prop_type}, 实际为 {properties[prop_name]['type']})")
        
        if missing_properties or wrong_types:
            message = ""
            if missing_properties:
                message += f"缺少属性: {', '.join(missing_properties)}. "
            if wrong_types:
                message += f"属性类型错误: {', '.join(wrong_types)}."
            
            return {
                "success": False,
                "message": message.strip()
            }
        
        return {
            "success": True,
            "message": "数据库结构验证通过"
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"验证数据库结构时出错: {str(e)}"
        } 