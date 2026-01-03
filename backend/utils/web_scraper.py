import requests
from bs4 import BeautifulSoup
import re
import json
import sys
import os
from markdownify import markdownify as md
from urllib.parse import urlparse

# 导入小红书 API - 多种方式尝试
XiaohongshuScraper = None

# 方式1：尝试从 backend.utils 包导入
try:
    from backend.utils.xiaohongshu_api import XiaohongshuScraper
    print("XiaohongshuScraper imported from backend.utils")
except ImportError:
    pass

# 方式2：尝试相对导入
if XiaohongshuScraper is None:
    try:
        from .xiaohongshu_api import XiaohongshuScraper
        print("XiaohongshuScraper imported from relative module")
    except ImportError:
        pass

# 方式3：尝试直接导入
if XiaohongshuScraper is None:
    try:
        from xiaohongshu_api import XiaohongshuScraper
        print("XiaohongshuScraper imported directly")
    except ImportError:
        pass

# 方式4：动态添加路径后导入
if XiaohongshuScraper is None:
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from xiaohongshu_api import XiaohongshuScraper
        print(f"XiaohongshuScraper imported via path: {current_dir}")
    except ImportError as e:
        print(f"Warning: All import attempts failed for XiaohongshuScraper: {e}")
        XiaohongshuScraper = None

if XiaohongshuScraper:
    print("XiaohongshuScraper is ready!")
else:
    print("XiaohongshuScraper not available, will use legacy parser")

def fetch_article_content(url):
    """
    Fetch and extract main content from a URL.
    Returns a dictionary with 'title' and 'content', or None on failure.
    """
    try:
        # Common headers to look like a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        
        # 检查是否是小红书短链或长链
        original_url = url
        is_xiaohongshu = 'xiaohongshu.com' in url or 'xhslink.com' in url
        
        # Requests with timeout
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        # Handle encoding
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        domain = urlparse(url).netloc
        
        # 小红书链接（包括短链）优先使用 API
        if is_xiaohongshu or 'xiaohongshu.com' in domain:
            return _handle_xiaohongshu(soup, response.text, url=original_url)
        elif 'weixin.qq.com' in domain:
            return _handle_wechat(soup)
        elif 'toutiao.com' in domain:
            return _handle_toutiao(soup)
        elif 'zhihu.com' in domain:
            return _handle_zhihu(soup)
        else:
            return _handle_generic(soup)

    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def _clean_soup(soup):
    """Remove unwanted tags"""
    for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript", "header", "aside"]):
        tag.decompose()
    return soup

def _handle_wechat(soup):
    """Parse WeChat Official Account articles"""
    article = soup.find(id='js_content') or soup.find(class_='rich_media_content')
    
    if not article:
        return _handle_generic(soup)

    # Handle lazy loading images
    for img in article.find_all('img'):
        if img.get('data-src'):
            img['src'] = img['data-src']
            
    title = ""
    if soup.find('h1'):
        title = soup.find('h1').get_text().strip()
    elif soup.find(id='activity-name'):
         title = soup.find(id='activity-name').get_text().strip()
    
    # Clean and convert
    _clean_soup(article)
    text = md(str(article), heading_style="ATX")
    
    return {
        'title': title,
        'content': text.strip()
    }

def _handle_toutiao(soup):
    """Parse Toutiao articles"""
    # Mobile Toutiao usually has 'article-content' or 'tt-article-content'
    article = soup.find(class_='article-content') or soup.find('article') or soup.find(class_='tt-article-content')
    
    if not article:
        # Fallback to generic if specific class not found
        return _handle_generic(soup)
        
    for img in article.find_all('img'):
        pass

    title = ""
    h1 = soup.find('h1') or soup.find(class_='title')
    if h1:
        title = h1.get_text().strip()
    
    _clean_soup(article)
    text = md(str(article), heading_style="ATX")
    
    return {
        'title': title,
        'content': text.strip()
    }

def _handle_xiaohongshu(soup, html_text, url=None):
    """
    使用 xiaohongshu_api.py 的高级解析逻辑处理小红书链接
    """
    print(f"[XHS] _handle_xiaohongshu called with url={url}")
    print(f"[XHS] XiaohongshuScraper available: {XiaohongshuScraper is not None}")
    
    if XiaohongshuScraper is None:
        print("[XHS] XiaohongshuScraper is None, using legacy")
        return _handle_xiaohongshu_legacy(soup, html_text)
    
    if not url:
        print("[XHS] URL is empty, using legacy")
        return _handle_xiaohongshu_legacy(soup, html_text)
    
    try:
        print(f"[XHS] Using XiaohongshuScraper for URL: {url}")
        scraper = XiaohongshuScraper(use_public_key=True)
        result = scraper.fetch_article(url)
        
        print(f"[XHS] API result success: {result.get('success')}")
        
        if not result.get('success'):
            print(f"[XHS] API failed: {result.get('message')}, falling back to legacy")
            return _handle_xiaohongshu_legacy(soup, html_text)
        
        data = result['data']
        title = data.get('title', '')
        desc = data.get('desc', '')
        nickname = data.get('nickname', '')
        note_id = data.get('noteId', '')
        user_id = data.get('userId', '')
        avatar = data.get('avatar', '')
        
        # 构建 Markdown 内容
        md_parts = []
        
        # 作者信息
        if nickname:
            md_parts.append(f"**作者**: {nickname}\n")
        if note_id:
            md_parts.append(f"**原文链接**: https://www.xiaohongshu.com/discovery/item/{note_id}\n")
        md_parts.append("---\n")
        
        # 描述内容
        if desc:
            md_parts.append("## 描述\n\n")
            md_parts.append(f"{desc}\n\n")
        
        # 处理图片 - 使用滑动组件
        images = data.get('data', [])
        if images:
            md_parts.append(f"\n## 图片 ({len(images)}张)\n\n")
            
            if len(images) > 1:
                # 多图滑动组件
                md_parts.append('<div class="xhs-slider" style="display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 10px; padding-bottom: 10px; -webkit-overflow-scrolling: touch;">\n')
                for i, img in enumerate(images, 1):
                    img_url = img.get('urlPre') or img.get('urlDefault', '')
                    if img_url:
                        # 使用图片代理绕过防盗链
                        proxy_url = f"https://i0.wp.com/{img_url.replace('https://', '').replace('http://', '')}"
                        md_parts.append(f'  <div style="flex: 0 0 100%; scroll-snap-align: start;"><img src="{proxy_url}" style="width: 100%; border-radius: 8px;" alt="图片{i}" /></div>\n')
                md_parts.append('</div>\n\n')
            else:
                # 单图
                img_url = images[0].get('urlPre') or images[0].get('urlDefault', '')
                if img_url:
                    proxy_url = f"https://i0.wp.com/{img_url.replace('https://', '').replace('http://', '')}"
                    md_parts.append(f"![{title or '图片'}]({proxy_url})\n\n")
        
        # 处理视频
        videos = data.get('video', [])
        if videos:
            md_parts.append(f"\n## 视频 ({len(videos)}个)\n\n")
            for i, video in enumerate(videos, 1):
                video_url = video.get('masterUrl', '')
                if video_url:
                    md_parts.append(f'<video src="{video_url}" controls style="width: 100%; border-radius: 8px; margin-top: 10px;"></video>\n\n')
        
        # 来源标注
        md_parts.append("---\n")
        md_parts.append("*来源: 小红书*\n")
        
        content = ''.join(md_parts)
        
        return {
            'title': title,
            'content': content,
            'platform': 'xiaohongshu',
            'raw_data': data
        }
    except Exception as e:
        print(f"[XHS] Error using XiaohongshuScraper: {e}")
        return _handle_xiaohongshu_legacy(soup, html_text)


def _handle_xiaohongshu_legacy(soup, html_text):
    """原有的简单解析逻辑，作为备选"""
    title = ""
    content = ""
    
    og_title = soup.find('meta', property='og:title')
    if og_title:
        title = og_title.get('content', '')
        
    og_desc = soup.find('meta', property='og:description')
    desc = ""
    if og_desc:
        desc = og_desc.get('content', '')
    
    image_md = ""
    og_image = soup.find('meta', property='og:image')
    if og_image:
        img_url = og_image.get('content', '')
        image_md = f"![{title}]({img_url})\n\n"

    content = f"{image_md}{desc}"
    
    if not content.strip():
        return _handle_generic(soup)
        
    return {
        'title': title,
        'content': content
    }

def _handle_zhihu(soup):
    """Parse Zhihu answers/articles"""
    article = soup.find(class_='RichContent-inner') or soup.find(class_='Post-RichText')
    
    if not article:
        return _handle_generic(soup)
        
    # Lazy load images
    for img in article.find_all('img'):
        if img.get('data-actualsrc'):
            img['src'] = img['data-actualsrc']
        elif img.get('data-original'):
            img['src'] = img['data-original']

    # Remove noscript
    for tag in article.find_all('noscript'):
        tag.decompose()

    title = ""
    if soup.find('h1'):
        title = soup.find('h1').get_text().strip()
        
    _clean_soup(article)
    text = md(str(article), heading_style="ATX")
    
    return {
        'title': title,
        'content': text.strip()
    }

def _handle_generic(soup):
    """Generic fallback parser"""
    _clean_soup(soup)
    
    # 1. Try to find <article>
    article = soup.find('article')
    
    # 2. Try common class names
    if not article:
        potential_classes = [
            'post-content', 'article-content', 'entry-content', 
            'content', 'main-content', 'news-content', 'rich_media_content',
            'detail-content', 'art_content'
        ]
        for cls in potential_classes:
            article = soup.find(class_=re.compile(cls, re.I))
            if article:
                break
                
    # 3. Fallback to main or body (if verified)
    if not article:
        article = soup.find('main')

    if not article:
        # Last resort: body
        article = soup.body

    if not article:
        return None
        
    # Extract Title
    title = ""
    if soup.title:
        title = soup.title.string
    if soup.find('h1'):
        title = soup.find('h1').get_text().strip()
    
    # Try to clean up images
    for img in article.find_all('img'):
        if img.get('data-src'):
            img['src'] = img['data-src']
            
    text = md(str(article), heading_style="ATX", strip=['script', 'style'])
    
    return {
        'title': title.strip(),
        'content': text.strip()
    }
