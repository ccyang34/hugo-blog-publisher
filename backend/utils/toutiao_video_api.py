#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
今日头条视频解析工具

功能特性:
- 支持短链接展开
- 自动提取 videoId
- 多清晰度视频地址获取
- Base64 解码真实视频地址
- 完善的错误处理
"""

import requests
import json
import re
import base64
import logging
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class ToutiaoVideoParser:
    """
    今日头条视频解析器
    
    支持解析今日头条、西瓜视频等字节跳动系视频链接
    """
    
    # 移动端 User-Agent（必须使用移动端UA）
    MOBILE_UA = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Mobile/15E148"
    )
    
    # 视频信息 API 端点
    VIDEO_API_ENDPOINTS = [
        "https://i.snssdk.com/video/urls/1/toutiao/mp4/{video_id}",
        "http://i.snssdk.com/video/urls/1/toutiao/mp4/{video_id}",
    ]
    
    # 支持的域名
    SUPPORTED_DOMAINS = [
        'm.toutiao.com',
        'www.toutiao.com',
        'toutiao.com',
        'www.ixigua.com',
        'ixigua.com',
        'm.ixigua.com',
    ]
    
    def __init__(self):
        """初始化解析器"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.MOBILE_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)
    
    def is_supported_url(self, url: str) -> bool:
        """
        检查URL是否为支持的视频链接
        
        Args:
            url: 待检查的URL
            
        Returns:
            是否为支持的链接
        """
        try:
            parsed = urlparse(url)
            return any(domain in parsed.netloc for domain in self.SUPPORTED_DOMAINS)
        except Exception:
            return False
    
    def parse_video(self, url: str) -> Dict:
        """
        解析视频链接，获取视频信息和播放地址
        
        Args:
            url: 视频URL（支持短链接和完整链接）
            
        Returns:
            包含视频信息的字典
        """
        try:
            self.logger.info(f"开始解析视频: {url}")
            
            # 1. 展开短链接
            expanded_url = self._expand_short_url(url)
            self.logger.info(f"展开后的URL: {expanded_url}")
            
            # 2. 获取页面内容并提取视频信息
            video_info = self._extract_video_info_from_page(expanded_url)
            
            if video_info.get('video_id'):
                # 3. 如果页面中没有直接提取到视频地址，通过 API 获取
                if not video_info.get('videos'):
                    video_urls = self._get_video_urls(video_info['video_id'])
                    video_info['videos'] = video_urls
                else:
                    self.logger.info(f"已从页面提取到 {len(video_info['videos'])} 个视频源")
            
            return {
                'success': True,
                'data': video_info,
                'original_url': url,
                'expanded_url': expanded_url,
                'parse_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"解析失败: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'original_url': url
            }
    
    def _expand_short_url(self, url: str) -> str:
        """
        展开短链接
        
        Args:
            url: 短链接URL
            
        Returns:
            展开后的完整URL
        """
        try:
            # 使用 HEAD 请求跟随重定向
            response = self.session.head(url, allow_redirects=True, timeout=10)
            return response.url
        except requests.exceptions.RequestException:
            # 如果 HEAD 失败，尝试 GET
            try:
                response = self.session.get(url, allow_redirects=True, timeout=15)
                return response.url
            except Exception:
                return url
    
    def _extract_video_info_from_page(self, url: str) -> Dict:
        """
        从页面中提取视频信息
        
        Args:
            url: 视频页面URL
            
        Returns:
            视频信息字典
        """
        video_info = {
            'video_id': None,
            'internal_video_id': None,  # 内部视频ID，用于获取播放地址
            'title': None,
            'cover': None,
            'author': None,
            'duration': None,
            'videos': [],
        }
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            html_content = response.text
            
            # 对URL编码的内容进行解码（页面中很多数据是URL编码的）
            from urllib.parse import unquote
            decoded_html = unquote(html_content)
            
            # 优先提取内部视频ID（v0开头的格式，这是获取播放地址需要的）
            # 例如: v02910g10002d5qn9knog65p59fe6bi0
            internal_vid_patterns = [
                r'"videoId"\s*:\s*"(v0[a-zA-Z0-9]+)"',
                r"tt-videoid='(v0[a-zA-Z0-9]+)'",
                r'"video_id"\s*:\s*"(v0[a-zA-Z0-9]+)"',
                r'video_id=(v0[a-zA-Z0-9]+)',
                # URL编码格式
                r'%22videoId%22%3A%22(v0[a-zA-Z0-9]+)%22',
                r"tt-videoid%3D'(v0[a-zA-Z0-9]+)'",
            ]
            
            # 先在解码后的内容中查找
            for pattern in internal_vid_patterns:
                match = re.search(pattern, decoded_html, re.IGNORECASE)
                if match:
                    internal_vid = match.group(1)
                    if internal_vid.startswith('v0') and len(internal_vid) > 20:
                        video_info['internal_video_id'] = internal_vid
                        video_info['video_id'] = internal_vid
                        self.logger.info(f"提取到内部视频ID: {internal_vid}")
                        break
            
            # 如果还没找到，在原始内容中查找
            if not video_info.get('internal_video_id'):
                for pattern in internal_vid_patterns:
                    match = re.search(pattern, html_content, re.IGNORECASE)
                    if match:
                        internal_vid = match.group(1)
                        if internal_vid.startswith('v0') and len(internal_vid) > 20:
                            video_info['internal_video_id'] = internal_vid
                            video_info['video_id'] = internal_vid
                            self.logger.info(f"提取到内部视频ID: {internal_vid}")
                            break
            
            # 如果没找到内部视频ID，尝试其他模式
            if not video_info['video_id']:
                video_id_patterns = [
                    r'/video/(\d+)',
                    r'"vid"\s*:\s*"([a-zA-Z0-9]+)"',
                    r'data-videoid="([a-zA-Z0-9]+)"',
                ]
                
                for pattern in video_id_patterns:
                    match = re.search(pattern, html_content, re.IGNORECASE)
                    if match:
                        potential_id = match.group(1)
                        if len(potential_id) > 10:
                            video_info['video_id'] = potential_id
                            self.logger.info(f"提取到 videoId: {potential_id}")
                            break
            
            # 尝试从页面中提取视频播放地址（新版今日头条直接在页面中嵌入了视频信息）
            # 查找 playAuthToken 或其他包含视频地址的数据
            playauth_pattern = r'"playAuthToken"\s*:\s*"([^"]+)"'
            match = re.search(playauth_pattern, html_content)
            if match:
                try:
                    playauth_data = match.group(1)
                    # URL解码
                    from urllib.parse import unquote
                    decoded_data = unquote(playauth_data)
                    # base64解码
                    try:
                        decoded_json = base64.b64decode(decoded_data).decode('utf-8')
                        playauth_json = json.loads(decoded_json)
                        if 'PlayUrl' in playauth_json:
                            play_url = playauth_json['PlayUrl']
                            video_info['videos'].append({
                                'quality': 'auto',
                                'url': play_url,
                            })
                            self.logger.info(f"从 playAuthToken 提取到视频地址")
                    except Exception:
                        pass
                except Exception as e:
                    self.logger.warning(f"解析 playAuthToken 失败: {e}")
            
            # 提取标题
            title_patterns = [
                r'"title"\s*:\s*"([^"]+)"',
                r'<title[^>]*>([^<]+)</title>',
                r'og:title"\s+content="([^"]+)"',
            ]
            for pattern in title_patterns:
                match = re.search(pattern, html_content)
                if match:
                    title = match.group(1).strip()
                    # 去除尾部的 "- 今日头条"
                    title = re.sub(r'\s*[-–—]\s*今日头条\s*$', '', title)
                    if title and title != '今日头条':
                        video_info['title'] = title
                        break
            
            # 提取封面图
            cover_patterns = [
                r'"posterUrl"\s*:\s*"([^"]+)"',
                r'"poster"\s*:\s*"([^"]+)"',
                r'"cover"\s*:\s*"([^"]+)"',
                r"tt-poster='([^']+)'",
                r'og:image"\s+content="([^"]+)"',
            ]
            for pattern in cover_patterns:
                match = re.search(pattern, html_content)
                if match:
                    cover = match.group(1)
                    # 处理转义的URL
                    cover = cover.replace('\\u0026', '&').replace('&amp;', '&')
                    video_info['cover'] = cover
                    break
            
            # 提取作者
            author_patterns = [
                r'"detailSource"\s*:\s*"([^"]+)"',
                r'"screenName"\s*:\s*"([^"]+)"',
                r'"source"\s*:\s*"([^"]+)"',
            ]
            for pattern in author_patterns:
                match = re.search(pattern, html_content)
                if match:
                    video_info['author'] = match.group(1)
                    break
            
            # 提取视频时长
            duration_pattern = r'"videoDuration"\s*:\s*(\d+)'
            match = re.search(duration_pattern, html_content)
            if match:
                video_info['duration'] = int(match.group(1))
                    
        except Exception as e:
            self.logger.warning(f"提取页面信息失败: {str(e)}")
        
        return video_info

    
    def _get_video_urls(self, video_id: str) -> List[Dict]:
        """
        通过 API 获取视频播放地址
        
        Args:
            video_id: 视频ID
            
        Returns:
            不同清晰度的视频地址列表
        """
        videos = []
        
        for endpoint_template in self.VIDEO_API_ENDPOINTS:
            try:
                endpoint = endpoint_template.format(video_id=video_id)
                self.logger.info(f"尝试获取视频信息: {endpoint}")
                
                response = self.session.get(endpoint, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('code') == 0 or 'data' in data:
                        video_data = data.get('data', {})
                        video_list = video_data.get('video_list', {})
                        
                        # 解析不同清晰度的视频
                        quality_map = {
                            'video_1': '360p',
                            'video_2': '480p',
                            'video_3': '720p',
                            'video_4': '1080p',
                        }
                        
                        for key, quality in quality_map.items():
                            if key in video_list:
                                video_item = video_list[key]
                                main_url = video_item.get('main_url', '')
                                
                                if main_url:
                                    # Base64 解码获取真实地址
                                    decoded_url = self._decode_video_url(main_url)
                                    if decoded_url:
                                        videos.append({
                                            'quality': quality,
                                            'url': decoded_url,
                                            'width': video_item.get('vwidth', 0),
                                            'height': video_item.get('vheight', 0),
                                            'size': video_item.get('size', 0),
                                        })
                        
                        if videos:
                            # 按清晰度排序（高清在前）
                            quality_order = {'1080p': 0, '720p': 1, '480p': 2, '360p': 3}
                            videos.sort(key=lambda x: quality_order.get(x['quality'], 99))
                            return videos
                            
            except Exception as e:
                self.logger.warning(f"API 请求失败 ({endpoint_template}): {str(e)}")
                continue
        
        # 如果 API 方式失败，尝试备用方法
        self.logger.info("尝试备用解析方法...")
        backup_videos = self._get_video_urls_backup(video_id)
        if backup_videos:
            return backup_videos
        
        return videos
    
    def _get_video_urls_backup(self, video_id: str) -> List[Dict]:
        """
        备用方法获取视频地址
        
        Args:
            video_id: 视频ID
            
        Returns:
            视频地址列表
        """
        videos = []
        
        # 尝试其他可能的 API 端点
        backup_endpoints = [
            f"https://www.ixigua.com/api/public/videov2/media/info?videoId={video_id}",
            f"https://www.ixigua.com/i{video_id}/",
        ]
        
        for endpoint in backup_endpoints:
            try:
                response = self.session.get(endpoint, timeout=15)
                if response.status_code == 200:
                    # 尝试从响应中提取视频地址
                    content = response.text
                    
                    # 查找 mp4 地址
                    mp4_pattern = r'(https?://[^"\'<>\s]+\.mp4[^"\'<>\s]*)'
                    matches = re.findall(mp4_pattern, content)
                    
                    for match in matches[:3]:  # 最多取3个
                        videos.append({
                            'quality': 'auto',
                            'url': match,
                        })
                    
                    if videos:
                        return videos
                        
            except Exception as e:
                self.logger.warning(f"备用方法失败: {str(e)}")
                continue
        
        return videos
    
    def _decode_video_url(self, encoded_url: str) -> Optional[str]:
        """
        Base64 解码视频地址
        
        Args:
            encoded_url: Base64 编码的URL
            
        Returns:
            解码后的URL或None
        """
        try:
            # 添加 padding
            padding = 4 - len(encoded_url) % 4
            if padding != 4:
                encoded_url += '=' * padding
            
            decoded_bytes = base64.b64decode(encoded_url)
            decoded_url = decoded_bytes.decode('utf-8')
            
            # 验证是否是有效的URL
            if decoded_url.startswith('http'):
                return decoded_url
            
        except Exception as e:
            self.logger.warning(f"Base64 解码失败: {str(e)}")
        
        return None


def parse_toutiao_video(url: str) -> Dict:
    """
    便捷函数：解析今日头条视频
    
    Args:
        url: 视频URL
        
    Returns:
        包含视频信息的字典
    """
    parser = ToutiaoVideoParser()
    return parser.parse_video(url)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python3 toutiao_video_api.py <今日头条视频URL>")
        print()
        print("示例:")
        print("  python3 toutiao_video_api.py https://m.toutiao.com/is/xxx/")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print("今日头条视频解析工具")
    print("=" * 60)
    print(f"目标URL: {url}")
    print("=" * 60)
    print()
    
    result = parse_toutiao_video(url)
    
    if result.get('success'):
        print("✅ 解析成功！")
        data = result['data']
        print(f"标题: {data.get('title', 'N/A')}")
        print(f"作者: {data.get('author', 'N/A')}")
        print(f"视频ID: {data.get('video_id', 'N/A')}")
        
        videos = data.get('videos', [])
        if videos:
            print(f"\n找到 {len(videos)} 个视频源:")
            for i, video in enumerate(videos, 1):
                print(f"  {i}. [{video.get('quality', 'N/A')}] {video.get('url', 'N/A')[:80]}...")
        else:
            print("\n⚠️ 未能获取到视频播放地址")
        
        print(f"\n封面: {data.get('cover', 'N/A')}")
    else:
        print(f"❌ 解析失败: {result.get('message')}")
        sys.exit(1)
