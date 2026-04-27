#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import re
import os
import time
import logging
from urllib.parse import urlparse, quote
from datetime import datetime
from typing import Dict, List, Optional, Union
from pathlib import Path


class XiaohongshuScraper:
    """
    小红书文章抓取工具
    
    功能特性：
    - 动态获取API端点
    - 多端点自动切换和重试
    - 完善的错误处理和容错机制
    - 支持图片和视频下载
    - 支持Markdown导出
    - 提供API接口供其他程序调用
    - 日志记录和缓存机制
    """
    
    def __init__(
        self,
        developer_id: Optional[str] = None,
        api_key: Optional[str] = None,
        use_public_key: bool = False
    ):
        """
        初始化抓取工具
        
        Args:
            developer_id: 开发者ID
            api_key: API密钥
            use_public_key: 是否使用公共密钥
        """
        # 使用默认开发者凭证
        self.developer_id = developer_id or '10011690'
        self.api_key = api_key or 'aa4e16c283b736df50d7ad47fdb9b7d7'
        self.use_public_key = use_public_key
        self.api_info_url = "https://www.apihz.cn/api/caijixiaohongshu.html"
        self.api_endpoints = []
        self.session = requests.Session()
        
        self._setup_logging()
        self._fetch_api_endpoints()
    
    def _setup_logging(self):
        """设置日志 - 仅控制台输出"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)
    
    def _fetch_api_endpoints(self):
        """
        从官网动态获取最新的API地址
        """
        try:
            self.logger.info("正在获取API端点...")
            response = self.session.get(self.api_info_url, timeout=10)
            response.raise_for_status()
            html_content = response.text

            pattern = r'http://[\d.]+/api/caiji/xiaohongshu\.php'
            endpoints = re.findall(pattern, html_content)

            if endpoints:
                self.api_endpoints = list(set(endpoints))
                self.logger.info(f"成功获取 {len(self.api_endpoints)} 个API端点")
                for i, endpoint in enumerate(self.api_endpoints, 1):
                    self.logger.info(f"  端点 {i}: {endpoint}")
            else:
                self.logger.warning("未能从网页获取API地址，使用默认地址")
                self.api_endpoints = self._get_default_endpoints()
        except Exception as e:
            self.logger.error(f"获取API地址失败: {str(e)}，使用默认地址")
            self.api_endpoints = self._get_default_endpoints()
    
    def _get_default_endpoints(self) -> List[str]:
        """获取默认API端点"""
        return [
            "http://101.35.2.25/api/caiji/xiaohongshu.php",
            "http://124.222.204.22/api/caiji/xiaohongshu.php",
            "http://81.68.149.132/api/caiji/xiaohongshu.php"
        ]

    
    def _extract_article_id(self, url: str) -> Optional[str]:
        """
        从URL中提取文章ID
        
        Args:
            url: 小红书文章URL
            
        Returns:
            文章ID或None
        """
        patterns = [
            r'/item/([a-f0-9]+)',
            r'/explore/([a-f0-9]+)',
            r'noteId=([a-f0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _resolve_short_link(self, short_url: str) -> Optional[str]:
        """
        解析短链接获取完整URL
        
        Args:
            short_url: 短链接URL
            
        Returns:
            完整URL或None
        """
        try:
            self.logger.info(f"正在解析短链接: {short_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = self.session.get(short_url, allow_redirects=True, timeout=10, headers=headers)
            full_url = response.url
            
            if full_url != short_url:
                self.logger.info(f"短链接解析成功: {full_url}")
                return full_url
            else:
                self.logger.warning(f"短链接未重定向，尝试从响应内容中提取")
                if 'xiaohongshu.com' in response.text:
                    pattern = r'https?://[^"\s]*xiaohongshu\.com[^"\s]*'
                    match = re.search(pattern, response.text)
                    if match:
                        full_url = match.group(0)
                        self.logger.info(f"从响应内容中提取到URL: {full_url}")
                        return full_url
                
                self.logger.error("无法从短链接获取完整URL")
                return None
        except Exception as e:
            self.logger.error(f"短链接解析失败: {str(e)}")
            return None
    
    def fetch_article(
        self,
        article_url: str,
        max_retries: int = 3,
        retry_delay: int = 2
    ) -> Dict:
        """
        抓取小红书文章内容
        
        Args:
            article_url: 小红书文章URL
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            
        Returns:
            包含文章数据的字典
        """
        if 'xhslink.com' in article_url:
            full_url = self._resolve_short_link(article_url)
            if full_url:
                article_url = full_url
            else:
                return {
                    'success': False,
                    'message': '短链接解析失败',
                    'code': 400
                }
        
        article_id = self._extract_article_id(article_url)
        if not article_id:
            return {
                'success': False,
                'message': '无法从URL中提取文章ID',
                'code': 400
            }
        
        params = {
            'url': article_url
        }

        if self.use_public_key:
            params['id'] = '88888888'
            params['key'] = '88888888'
        else:
            if not self.developer_id or not self.api_key:
                return {
                    'success': False,
                    'message': '未配置开发者ID和API_KEY',
                    'code': 400
                }
            params['id'] = self.developer_id
            params['key'] = self.api_key

        params['hctype'] = '1'

        last_error = None
        for retry in range(max_retries):
            for endpoint in self.api_endpoints:
                try:
                    self.logger.info(f"尝试端点: {endpoint}")
                    response = self.session.get(endpoint, params=params, timeout=30)
                    response.raise_for_status()
                    result = response.json()

                    if result.get('code') == 200:
                        return {
                            'success': True,
                            'data': result,
                            'endpoint': endpoint
                        }
                    elif result.get('code') == 400:
                        error_msg = result.get('msg', '未知错误')
                        self.logger.error(f"API返回错误: {error_msg}")
                        return {
                            'success': False,
                            'message': error_msg,
                            'code': 400
                        }
                    else:
                        self.logger.warning(f"API返回非200状态码: {result.get('code')}")

                except requests.exceptions.Timeout:
                    last_error = "请求超时"
                    self.logger.warning(f"端点 {endpoint} 请求超时")
                    continue
                except requests.exceptions.RequestException as e:
                    last_error = str(e)
                    self.logger.warning(f"端点 {endpoint} 请求失败: {str(e)}")
                    continue
                except json.JSONDecodeError as e:
                    last_error = f"JSON解析失败: {str(e)}"
                    self.logger.warning(f"端点 {endpoint} 返回数据格式错误")
                    continue
            
            if retry < max_retries - 1:
                self.logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
        
        return {
            'success': False,
            'message': f'所有端点均失败，最后错误: {last_error}',
            'code': 500
        }
    
    def download_media(
        self,
        url: str,
        save_dir: str = 'downloads',
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        下载媒体文件（图片或视频）
        
        Args:
            url: 媒体文件URL
            save_dir: 保存目录
            filename: 文件名（可选）
            
        Returns:
            保存的文件路径或None
        """
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        if not filename:
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)
            if not filename or '.' not in filename:
                filename = f"media_{int(time.time())}"
        
        filepath = os.path.join(save_dir, filename)
        
        try:
            self.logger.info(f"正在下载: {url}")
            response = self.session.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.logger.info(f"下载完成: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"下载失败: {str(e)}")
            return None
    
    def download_article_media(
        self,
        article_data: Dict,
        save_dir: str = 'downloads',
        download_images: bool = True,
        download_videos: bool = True
    ) -> Dict[str, List[str]]:
        """
        下载文章中的所有媒体文件
        
        Args:
            article_data: 文章数据
            save_dir: 保存目录
            download_images: 是否下载图片
            download_videos: 是否下载视频
            
        Returns:
            包含下载文件路径的字典
        """
        result = {
            'images': [],
            'videos': []
        }
        
        if not article_data.get('success'):
            return result
        
        data = article_data['data']
        title = data.get('title', 'article')
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        article_dir = os.path.join(save_dir, safe_title)
        
        if download_images:
            images = data.get('data', [])
            for i, img in enumerate(images, 1):
                url_default = img.get('urlDefault', '') or img.get('urlPre', '')
                if url_default:
                    ext = self._get_file_extension(url_default)
                    filename = f"image_{i}{ext}"
                    filepath = self.download_media(url_default, article_dir, filename)
                    if filepath:
                        result['images'].append(filepath)
        
        if download_videos:
            videos = data.get('video', [])
            for i, video in enumerate(videos, 1):
                master_url = video.get('masterUrl', '')
                if master_url:
                    ext = self._get_file_extension(master_url)
                    filename = f"video_{i}{ext}"
                    filepath = self.download_media(master_url, article_dir, filename)
                    if filepath:
                        result['videos'].append(filepath)
        
        return result
    
    def _get_file_extension(self, url: str) -> str:
        """从URL中获取文件扩展名"""
        parsed = urlparse(url)
        path = parsed.path
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi']:
            return ext
        return '.jpg'
    
    def save_to_markdown(
        self,
        article_data: Dict,
        output_dir: str = 'xiaohongshu_articles',
        include_media_links: bool = True
    ) -> Optional[str]:
        """
        将文章数据保存为Markdown文件
        
        Args:
            article_data: 文章数据
            output_dir: 输出目录
            include_media_links: 是否包含媒体链接
            
        Returns:
            保存的文件路径或None
        """
        if not article_data.get('success'):
            self.logger.error(f"保存失败: {article_data.get('message')}")
            return None
        
        data = article_data['data']
        
        title = data.get('title', '无标题')
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        filename = f'{safe_title}.md'
        filepath = os.path.join(output_dir, filename)
        
        md_content = []
        md_content.append(f'# {title}\n')
        md_content.append(f'**作者**: {data.get("nickname", "N/A")}\n')
        md_content.append(f'**文章ID**: {data.get("noteId", "N/A")}\n')
        md_content.append(f'**用户ID**: {data.get("userId", "N/A")}\n')
        
        avatar = data.get('avatar')
        if avatar:
            md_content.append(f'**头像**: [{data.get("nickname", "作者")}]({avatar})\n')
        
        md_content.append(f'**原文链接**: https://www.xiaohongshu.com/discovery/item/{data.get("noteId", "")}\n')
        md_content.append('---\n')
        
        desc = data.get('desc', '')
        if desc:
            md_content.append('## 描述\n\n')
            md_content.append(f'{desc}\n')
        
        images = data.get('data', [])
        if images and include_media_links:
            md_content.append(f'\n## 图片 ({len(images)}张)\n\n')
            for i, img in enumerate(images, 1):
                md_content.append(f'### 图片 {i}\n\n')
                url_pre = img.get('urlPre', '')
                url_default = img.get('urlDefault', '')
                height = img.get('height', 0)
                width = img.get('width', 0)
                
                if url_pre:
                    md_content.append(f'![图片{i}]({url_pre})\n\n')
                    md_content.append(f'- **尺寸**: {width}x{height}\n')
                    md_content.append(f'- **预览链接**: {url_pre}\n')
                    if url_default:
                        md_content.append(f'- **原图链接**: {url_default}\n')
                    md_content.append('\n')
        
        videos = data.get('video', [])
        if videos and include_media_links:
            md_content.append(f'\n## 视频 ({len(videos)}个)\n\n')
            for i, video in enumerate(videos, 1):
                md_content.append(f'### 视频 {i}\n\n')
                master_url = video.get('masterUrl', '')
                width = video.get('width', 0)
                height = video.get('height', 0)
                duration = video.get('duration', 0) / 1000
                quality = video.get('qualityType', 'N/A')
                
                if master_url:
                    md_content.append(f'**视频链接**: {master_url}\n')
                    md_content.append(f'- **分辨率**: {width}x{height}\n')
                    md_content.append(f'- **时长**: {duration:.2f}秒\n')
                    md_content.append(f'- **质量**: {quality}\n')
                    md_content.append('\n')
        
        md_content.append('---\n')
        md_content.append(f'*抓取时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*\n')
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(''.join(md_content))
            self.logger.info(f"Markdown文件已保存: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"保存Markdown文件失败: {str(e)}")
            return None


def scrape_xiaohongshu(
    url: str,
    save_markdown: bool = True,
    download_media: bool = False,
    output_dir: str = 'xiaohongshu_articles',
    developer_id: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict:
    """
    便捷函数：抓取小红书文章
    
    Args:
        url: 小红书文章URL
        save_markdown: 是否保存为Markdown
        download_media: 是否下载媒体文件
        output_dir: 输出目录
        developer_id: 开发者ID
        api_key: API密钥
        
    Returns:
        包含抓取结果的字典
    """
    scraper = XiaohongshuScraper(
        developer_id=developer_id,
        api_key=api_key,
        use_public_key=True
    )
    
    result = scraper.fetch_article(url)
    
    if result.get('success'):
        if save_markdown:
            md_path = scraper.save_to_markdown(result, output_dir)
            result['markdown_path'] = md_path
        
        if download_media:
            media_paths = scraper.download_article_media(result, output_dir)
            result['media_paths'] = media_paths
    
    return result


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python3 xiaohongshu_api.py <小红书文章URL>")
        print("  python3 xiaohongshu_api.py <小红书文章URL> --download-media")
        sys.exit(1)
    
    url = sys.argv[1]
    download_media = '--download-media' in sys.argv
    
    print("小红书文章抓取工具")
    print("=" * 60)
    print(f"目标URL: {url}")
    print(f"下载媒体: {'是' if download_media else '否'}")
    print("=" * 60)
    print()
    
    result = scrape_xiaohongshu(
        url=url,
        save_markdown=True,
        download_media=download_media
    )
    
    if result.get('success'):
        print("✅ 抓取成功！")
        data = result['data']
        print(f"标题: {data.get('title')}")
        print(f"作者: {data.get('nickname')}")
        
        if 'markdown_path' in result:
            print(f"\nMarkdown文件: {result['markdown_path']}")
        
        if 'media_paths' in result:
            media = result['media_paths']
            print(f"\n下载的图片: {len(media.get('images', []))} 张")
            print(f"下载的视频: {len(media.get('videos', []))} 个")
    else:
        print(f"❌ 抓取失败: {result.get('message')}")
        sys.exit(1)
