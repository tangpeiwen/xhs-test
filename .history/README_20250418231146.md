# 小红书内容提取器 (Xiaohongshu Content Extractor)

这个项目可以帮助你通过iOS快捷指令提取小红书内容（包括文字和图片）并保存到备忘录。

## 功能

- 提取小红书帖子的标题、描述和图片
- 将内容保存到iOS备忘录
- 通过iOS快捷指令实现一键操作

## 安装

1. 确保已安装Conda和Git
2. 克隆此仓库：
   ```bash
   git clone https://github.com/yourusername/xhs-example.git
   cd xhs-example
   ```
3. 创建Conda环境：
   ```bash
   conda env create -f environment.yml
   ```
4. 激活环境：
   ```bash
   conda activate xhs
   ```

## 运行API服务器

1. 运行服务器：
   ```bash
   python run_server.py start
   ```
2. 获取本地IP地址（用于配置快捷指令）：
   ```bash
   python run_server.py get-ip
   ```

## 配置iOS快捷指令

1. 在iPhone或iPad上打开"快捷指令"应用
2. 创建新的快捷指令
3. 添加以下步骤：
   - 接收剪贴板中的小红书链接
   - 使用"获取网页内容"，URL设置为 `http://你的IP地址:8000/extract`
   - 内容类型选择 `JSON`
   - 方法选择 `POST`
   - 请求正文设置为 `{"url": "剪贴板内容"}`
   - 解析JSON响应
   - 添加"创建备忘录"操作
   - 设置标题为 `{解析后的标题}`
   - 设置正文为 `{解析后的描述} \n\n原始链接: {解析后的原始URL}`
   - 对于每个图片，添加到备忘录正文中

## 使用方法

1. 在小红书APP中，找到你想保存的帖子
2. 点击分享按钮，然后选择"复制链接"
3. 运行你创建的快捷指令
4. 内容和图片会自动保存到备忘录中

## 常见问题

- **服务器无法连接**：确保手机和运行服务器的电脑在同一个WiFi网络中
- **图片无法保存**：检查API返回的图片格式是否正确
- **内容无法提取**：某些小红书内容可能受到保护，无法提取

## 技术细节

本项目使用：
- FastAPI 构建API
- BeautifulSoup4 解析网页内容
- Typer 构建命令行界面
- Uvicorn 作为ASGI服务器

## 许可

MIT 