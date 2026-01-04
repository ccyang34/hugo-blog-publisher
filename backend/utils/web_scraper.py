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
            return _handle_wechat(soup, url=url)
        elif 'toutiao.com' in domain:
            return _handle_toutiao(soup, url=url)
        elif 'zhihu.com' in domain:
            return _handle_zhihu(soup, url=url)
        else:
            return _handle_generic(soup, url=url)

    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def _clean_soup(soup):
    """Remove unwanted tags"""
    for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript", "header", "aside"]):
        tag.decompose()
    return soup

def _handle_wechat(soup, url=None):
    """Parse WeChat Official Account articles - 视频保留在原位置"""
    article = soup.find(id='js_content') or soup.find(class_='rich_media_content')
    
    if not article:
        return _handle_generic(soup, url=url)

    # Handle lazy loading images
    for img in article.find_all('img'):
        if img.get('data-src'):
            img['src'] = img['data-src']
    
    # 在原位置将视频标签转换为可识别的 HTML 格式
    video_count = 0
    
    # 1. 处理 iframe 视频（腾讯视频、微信视频号等）- 原位保留
    for iframe in article.find_all('iframe'):
        src = iframe.get('data-src') or iframe.get('src', '')
        if src and ('v.qq.com' in src or 'mp.weixin.qq.com' in src or 'channels' in src or 'mpvideo' in src):
            video_count += 1
            # 创建新的 iframe 标签并替换原标签
            new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
            new_tag.string = f'[[VIDEO_IFRAME:{src}]]'
            iframe.replace_with(new_tag)
    
    # 2. 处理 mpvideo 标签（微信自有视频标签）- 原位替换
    for mpvideo in article.find_all('mpvideo'):
        src = mpvideo.get('data-src') or mpvideo.get('src', '')
        cover = mpvideo.get('data-cover') or mpvideo.get('cover', '')
        video_id = mpvideo.get('data-vidtype') or mpvideo.get('data-videoid', '')
        if not src and video_id:
            src = f"https://mp.weixin.qq.com/mp/videoplayer?action=mpvideo&__biz=&vid={video_id}"
        if src or cover:
            video_count += 1
            new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
            new_tag.string = f'[[VIDEO_MPVIDEO:{src}:{cover}]]'
            mpvideo.replace_with(new_tag)
    
    # 3. 处理 wx-video 标签（视频号视频）- 原位替换
    for wxvideo in article.find_all(['wx-video', 'mp-common-videosnap']):
        src = wxvideo.get('data-src') or wxvideo.get('src', '')
        cover = wxvideo.get('data-poster') or wxvideo.get('data-cover', '')
        video_count += 1
        new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
        new_tag.string = f'[[VIDEO_WXVIDEO:{src}:{cover}]]'
        wxvideo.replace_with(new_tag)
    
    # 4. 处理标准 video 标签 - 原位保留
    for video in article.find_all('video'):
        src = video.get('data-src') or video.get('src', '')
        poster = video.get('poster', '')
        source = video.find('source')
        if source and not src:
            src = source.get('src', '')
        if src or poster:
            video_count += 1
            new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
            new_tag.string = f'[[VIDEO_STANDARD:{src}:{poster}]]'
            video.replace_with(new_tag)
            
    title = ""
    if soup.find('h1'):
        title = soup.find('h1').get_text().strip()
    elif soup.find(id='activity-name'):
         title = soup.find(id='activity-name').get_text().strip()
    
    # 移除不需要的标签，但保留媒体相关的
    for tag in article(["script", "style", "nav", "footer", "noscript", "header", "aside"]):
        tag.decompose()
    
    # 转换为 Markdown
    text = md(str(article), heading_style="ATX")
    
    # 将视频占位符还原为正确的嵌入代码
    def replace_video_placeholder(match):
        placeholder = match.group(0)
        if placeholder.startswith('[[VIDEO_IFRAME:'):
            src = placeholder[15:-2]
            return f'\n\n<iframe src="{src}" width="100%" height="360" frameborder="0" allowfullscreen></iframe>\n\n'
        elif placeholder.startswith('[[VIDEO_MPVIDEO:'):
            parts = placeholder[16:-2].split(':', 1)
            src = parts[0] if parts else ''
            cover = parts[1] if len(parts) > 1 else ''
            if src:
                return f'\n\n<iframe src="{src}" width="100%" height="360" frameborder="0" allowfullscreen></iframe>\n\n'
            elif cover:
                return f'\n\n![视频封面]({cover})\n\n'
            return ''
        elif placeholder.startswith('[[VIDEO_WXVIDEO:'):
            parts = placeholder[16:-2].split(':', 1)
            src = parts[0] if parts else ''
            cover = parts[1] if len(parts) > 1 else ''
            result = ''
            if cover:
                result += f'\n\n![视频号视频封面]({cover})\n\n'
            if src:
                result += f'*[点击观看视频号视频]({src})*\n\n'
            return result if result else ''
        elif placeholder.startswith('[[VIDEO_STANDARD:'):
            parts = placeholder[17:-2].split(':', 1)
            src = parts[0] if parts else ''
            poster = parts[1] if len(parts) > 1 else ''
            if src:
                return f'\n\n<video src="{src}" controls style="width: 100%; border-radius: 8px;"></video>\n\n'
            elif poster:
                return f'\n\n![视频封面]({poster})\n\n'
            return ''
        return placeholder
    
    # 使用正则替换所有视频占位符（注意 markdownify 会转义方括号和下划线）
    # 先还原转义：\_ -> _ 
    text = text.replace('\\_', '_')
    text = re.sub(r'\[\[VIDEO_[A-Z]+:[^\]]*\]\]', replace_video_placeholder, text)
    
    # 添加底部来源链接
    text = text.strip()
    text += "\n\n---\n"
    if url:
        text += f"*来源: [微信公众号]({url})*\n"
    else:
        text += "*来源: 微信公众号*\n"
    
    return {
        'title': title,
        'content': text
    }

def _handle_toutiao(soup, url=None):
    """Parse Toutiao articles"""
    # Mobile Toutiao usually has 'article-content' or 'tt-article-content'
    article = soup.find(class_='article-content') or soup.find('article') or soup.find(class_='tt-article-content')
    
    if not article:
        # Fallback to generic if specific class not found
        return _handle_generic(soup, url=url)
        
    for img in article.find_all('img'):
        pass

    title = ""
    h1 = soup.find('h1') or soup.find(class_='title')
    if h1:
        title = h1.get_text().strip()
    
    _clean_soup(article)
    text = md(str(article), heading_style="ATX")
    
    # 添加底部来源链接
    text = text.strip()
    text += "\n\n---\n"
    if url:
        text += f"*来源: [今日头条]({url})*\n"
    else:
        text += "*来源: 今日头条*\n"
    
    return {
        'title': title,
        'content': text
    }

def _handle_xiaohongshu(soup, html_text, url=None):
    """
    使用 xiaohongshu_api.py 的高级解析逻辑处理小红书链接
    如果抓取后 title 为 '小红书'，说明抓取失败，将进行重试
    """
    print(f"[XHS] _handle_xiaohongshu called with url={url}")
    print(f"[XHS] XiaohongshuScraper available: {XiaohongshuScraper is not None}")
    
    if XiaohongshuScraper is None:
        print("[XHS] XiaohongshuScraper is None, using legacy")
        return _handle_xiaohongshu_legacy(soup, html_text)
    
    if not url:
        print("[XHS] URL is empty, using legacy")
        return _handle_xiaohongshu_legacy(soup, html_text)
    
    def try_fetch(scraper, url, attempt_name):
        """尝试抓取并检查结果"""
        print(f"[XHS] {attempt_name}: Fetching URL: {url}")
        result = scraper.fetch_article(url)
        
        if not result.get('success'):
            print(f"[XHS] {attempt_name}: API failed: {result.get('message')}")
            return None
        
        data = result['data']
        title = data.get('title', '')
        
        # 检查是否抓取失败（title 为 '小红书' 表示未正确获取数据）
        if title == '小红书' or not title:
            print(f"[XHS] {attempt_name}: Got invalid title '{title}', treating as failure")
            return None
        
        print(f"[XHS] {attempt_name}: Success! Title: {title}")
        return data
    
    try:
        # 第一次尝试：使用开发者凭证
        scraper = XiaohongshuScraper(use_public_key=False)
        data = try_fetch(scraper, url, "Attempt 1 (Developer Key)")
        
        if data is None:
            # 第二次尝试：强制刷新端点并使用公共凭证
            print("[XHS] Retrying with public key and refreshed endpoints...")
            scraper = XiaohongshuScraper(use_public_key=True)
            data = try_fetch(scraper, url, "Attempt 2 (Public Key)")
        
        if data is None:
            # 第三次尝试：等待60秒后重试
            print("[XHS] Waiting 60 seconds before final retry...")
            import time
            time.sleep(60)
            scraper = XiaohongshuScraper(use_public_key=False)
            data = try_fetch(scraper, url, "Attempt 3 (After 60s wait)")
        
        if data is None:
            print("[XHS] All attempts failed, using legacy parser")
            return _handle_xiaohongshu_legacy(soup, html_text)
        
        # 成功获取数据，构建内容
        title = data.get('title', '')
        desc = data.get('desc', '')
        nickname = data.get('nickname', '')
        note_id = data.get('noteId', '')
        user_id = data.get('userId', '')
        avatar = data.get('avatar', '')
        
        # 构建 Markdown 内容
        md_parts = []
        
        # 作者信息（原文链接移到底部）
        if nickname:
            md_parts.append(f"**作者**: {nickname}\n")
        md_parts.append("---\n")
        
        # 描述内容
        if desc:
            md_parts.append("## 描述\n\n")
            md_parts.append(f"{desc}\n\n")
        
        # 处理图片 - 竖向顺序排列
        images = data.get('data', [])
        if images:
            md_parts.append(f"\n## 图片 ({len(images)}张)\n\n")
            
            for i, img in enumerate(images, 1):
                # 优先使用原图 urlDefault，不存在则使用预览图 urlPre
                img_url = img.get('urlDefault') or img.get('urlPre', '')
                if img_url:
                    # 使用图片代理绕过防盗链
                    proxy_url = f"https://i0.wp.com/{img_url.replace('https://', '').replace('http://', '')}"
                    md_parts.append(f"![图片{i}]({proxy_url})\n\n")
        
        # 处理视频
        videos = data.get('video', [])
        if videos:
            md_parts.append(f"\n## 视频 ({len(videos)}个)\n\n")
            for i, video in enumerate(videos, 1):
                video_url = video.get('masterUrl', '')
                if video_url:
                    md_parts.append(f'<video src="{video_url}" controls style="width: 100%; border-radius: 8px; margin-top: 10px;"></video>\n\n')
        
        # 来源标注（包含原文链接）
        md_parts.append("---\n")
        if note_id:
            md_parts.append(f"*来源: [小红书](https://www.xiaohongshu.com/discovery/item/{note_id})*\n")
        else:
            md_parts.append("*来源: 小红书*\n")
        
        content = ''.join(md_parts)
        
        # 如果没有描述内容（纯图片笔记），跳过 AI 排版
        skip_ai = not desc or desc.strip() == ''
        if skip_ai:
            print("[XHS] No description content, will skip AI formatting")
        
        return {
            'title': title,
            'content': content,
            'platform': 'xiaohongshu',
            'raw_data': data,
            'skip_ai_format': skip_ai  # 纯图片笔记跳过 AI 排版
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

def _handle_zhihu(soup, url=None):
    """Parse Zhihu answers/articles"""
    article = soup.find(class_='RichContent-inner') or soup.find(class_='Post-RichText')
    
    if not article:
        return _handle_generic(soup, url=url)
        
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
    
    # 添加底部来源链接
    text = text.strip()
    text += "\n\n---\n"
    if url:
        text += f"*来源: [知乎]({url})*\n"
    else:
        text += "*来源: 知乎*\n"
    
    return {
        'title': title,
        'content': text
    }

def _handle_generic(soup, url=None):
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
    
    # 添加底部来源链接
    text = text.strip()
    if url:
        text += "\n\n---\n"
        text += f"*来源: [原文链接]({url})*\n"
    
    return {
        'title': title.strip() if title else '',
        'content': text
    }
