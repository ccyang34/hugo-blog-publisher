import requests
from bs4 import BeautifulSoup
import re
import json
import sys
import os
from markdownify import markdownify as md
from urllib.parse import urlparse, unquote

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
    """Parse WeChat Official Account articles - 支持标准图文和短图文/图片集模板"""
    article = soup.find(id='js_content') or soup.find(class_='rich_media_content')
    
    # 获取标题
    title = ""
    if soup.find('h1'):
        title = soup.find('h1').get_text().strip()
    elif soup.find(id='activity-name'):
         title = soup.find(id='activity-name').get_text().strip()
    elif soup.find(class_='rich_media_title'):
         title = soup.find(class_='rich_media_title').get_text().strip()

    # 如果找不到标准正文容器，尝试处理“短图文/图片集”模板
    if not article:
        html_text = str(soup)
        
        # 1. 提取短图文特有的图片列表和描述
        # 数据通常在 window.picture_page_info_list 或类似变量中
        import json
        
        # 模拟微信内部的 JsDecode (虽然目前观察到的 cdn_url 通常是明文或带简单编码)
        def wechat_js_decode(s):
            if not s: return ""
            # 去掉可能的外部引号和 JsDecode('') 包装
            s = re.sub(r"^JsDecode\(['\"](.*)['\"]\)$", r"\1", s)
            return s.replace('\\x26', '&').replace('\\x2f', '/')

        # 尝试从 JS 变量提取图片信息
        img_list = []
        # 匹配 picture_page_info_list 中的 cdn_url
        img_matches = re.findall(r"cdn_url:\s*(?:JsDecode\()?['\"](.*?)['\"]", html_text)
        for img_url in img_matches:
            decoded_url = wechat_js_decode(img_url)
            if decoded_url and 'mmbiz.qpic.cn' in decoded_url and decoded_url not in img_list:
                img_list.append(decoded_url)

        # 提取描述文本 (位于 #js_image_desc 或相关变量)
        desc_text = ""
        desc_elem = soup.find(id='js_image_desc') or soup.find(class_='js_underline_content')
        if desc_elem:
            desc_text = desc_elem.get_text(separator='\n').strip()
        
        # 如果提取到了图片或描述，则手动构建内容
        if img_list or desc_text:
            md_parts = []
            if desc_text:
                md_parts.append(desc_text + "\n\n")
            
            for i, img_url in enumerate(img_list, 1):
                # 使用代理绕过防盗链
                proxy_url = f"https://i0.wp.com/{img_url.replace('https://', '').replace('http://', '')}"
                md_parts.append(f"![图片{i}]({proxy_url})\n\n")
            
            content = "".join(md_parts).strip()
            
            # 补全来源
            content += "\n\n---\n"
            if url:
                content += f"*来源: [微信公众号]({url})*\n"
            else:
                content += "*来源: 微信公众号*\n"
                
            return {
                'title': title,
                'content': content
            }

        # 如果还是找不到，回退到通用解析
        return _handle_generic(soup, url=url)

    # --- 以下为标准文章处理逻辑 ---
    # Handle lazy loading images - 使用代理绕过防盗链
    for img in article.find_all('img'):
        src = img.get('data-src') or img.get('src', '')
        if src and ('mmbiz.qpic.cn' in src or 'mmbiz.qlogo.cn' in src):
            # 使用 WordPress 图片代理绕过微信防盗链
            proxy_url = f"https://i0.wp.com/{src.replace('https://', '').replace('http://', '')}"
            img['src'] = proxy_url
        elif img.get('data-src'):
            img['src'] = img['data-src']
    
    # 在原位置将视频标签转换为可识别的 HTML 格式，同时提取封面图
    video_count = 0
    video_covers = {}  # 存储视频封面图
    
    # 1. 处理 iframe 视频（腾讯视频、微信视频号等）
    for iframe in article.find_all('iframe'):
        src = iframe.get('data-src') or iframe.get('src', '')
        cover = iframe.get('data-cover') or iframe.get('data-poster') or ''
        if src and ('v.qq.com' in src or 'mp.weixin.qq.com' in src or 'channels' in src or 'mpvideo' in src):
            video_count += 1
            video_covers[video_count] = cover
            new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
            new_tag.string = f'[[VIDEO_WECHAT:{video_count}]]'
            iframe.replace_with(new_tag)
    
    # 2. 处理 mpvideo 标签（微信自有视频标签）
    for mpvideo in article.find_all('mpvideo'):
        src = mpvideo.get('data-src') or mpvideo.get('src', '')
        cover = mpvideo.get('data-cover') or mpvideo.get('cover') or mpvideo.get('data-poster', '')
        video_id = mpvideo.get('data-vidtype') or mpvideo.get('data-videoid', '')
        if src or cover or video_id:
            video_count += 1
            video_covers[video_count] = cover
            new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
            new_tag.string = f'[[VIDEO_WECHAT:{video_count}]]'
            mpvideo.replace_with(new_tag)
    
    # 3. 处理 wx-video 标签（视频号视频）
    for wxvideo in article.find_all(['wx-video', 'mp-common-videosnap']):
        cover = wxvideo.get('data-poster') or wxvideo.get('data-cover') or wxvideo.get('data-headimgurl', '')
        video_count += 1
        video_covers[video_count] = cover
        new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
        new_tag.string = f'[[VIDEO_WECHAT:{video_count}]]'
        wxvideo.replace_with(new_tag)
    
    # 4. 处理标准 video 标签
    for video in article.find_all('video'):
        src = video.get('data-src') or video.get('src', '')
        poster = video.get('poster', '')
        source = video.find('source')
        if source and not src:
            src = source.get('src', '')
        if src or poster:
            video_count += 1
            video_covers[video_count] = poster
            new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
            new_tag.string = f'[[VIDEO_WECHAT:{video_count}]]'
            video.replace_with(new_tag)
            
    # 移除不需要的标签
    for tag in article(["script", "style", "nav", "footer", "noscript", "header", "aside"]):
        tag.decompose()
    
    # 转换为 Markdown
    text = md(str(article), heading_style="ATX")
    
    # 将视频占位符替换为封面图+链接（类似图片处理方式）
    def replace_video_placeholder(match):
        placeholder = match.group(0)
        if placeholder.startswith('[[VIDEO_WECHAT:'):
            video_num = int(placeholder[15:-2])
            cover = video_covers.get(video_num, '')
            
            # 如果有封面图，使用代理显示封面（先解码 URL 编码）
            cover = unquote(cover) if cover else ''
            if cover and ('mmbiz.qpic.cn' in cover or 'mmbiz.qlogo.cn' in cover):
                proxy_cover = f"https://i0.wp.com/{cover.replace('https://', '').replace('http://', '')}"
                if url:
                    return f'\n\n[![📺 点击观看视频]({proxy_cover})]({url})\n\n'
                else:
                    return f'\n\n![📺 视频封面]({proxy_cover})\n\n'
            elif cover:
                # 封面不是微信域名，直接使用
                if url:
                    return f'\n\n[![📺 点击观看视频]({cover})]({url})\n\n'
                else:
                    return f'\n\n![📺 视频封面]({cover})\n\n'
            else:
                # 没有封面图，使用文字提示卡片
                if url:
                    return f'\n\n> 📺 **视频内容**\n>\n> 由于微信视频限制，请 **[点击查看原文观看视频]({url})**\n\n'
                else:
                    return f'\n\n> 📺 **视频内容** - 此处包含视频，请在微信中查看原文\n\n'
        return placeholder
    
    # 使用正则替换所有视频占位符
    text = text.replace('\\_', '_')
    text = re.sub(r'\[\[VIDEO_WECHAT:\d+\]\]', replace_video_placeholder, text)
    
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
