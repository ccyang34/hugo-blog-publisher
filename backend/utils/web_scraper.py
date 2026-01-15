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

def _get_wechat_video_url(vid, article_url=None):
    """
    通过 VID 获取微信视频的真实 MP4 地址
    """
    url = f"https://mp.weixin.qq.com/mp/videoplayer?action=get_mp_video_play_url&preview=0&vid={vid}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': article_url if article_url else 'https://mp.weixin.qq.com/',
        'Origin': 'https://mp.weixin.qq.com'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # 即使状态码是 200，也可能返回错误 JSON，但通常 raise_for_status 够了
        if response.status_code != 200:
            print(f"Failed to get video URL for {vid}, status: {response.status_code}")
            return None
            
        data = response.json()
        
        if 'url_info' in data and data['url_info']:
            # 通常会有多个分辨率，取第一个或质量最好的
            video_info = data['url_info'][0]
            return video_info.get('url')
            
        return None
        
    except Exception as e:
        print(f"Error fetching video URL for {vid}: {e}")
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
        import json
        
        # 增强版 JsDecode，处理更多转义字符
        def wechat_js_decode(s):
            if not s: return ""
            # 去掉可能的外部包装
            s = re.sub(r"^JsDecode\(['\"](.*)['\"]\)$", r"\1", s)
            # 处理常见的转义
            map_replace = {
                '\\x26': '&', '\\x2f': '/', '\\x0a': '\n', 
                '\\x3d': '=', '\\x22': '"', '\\x27': "'",
                '&amp;': '&', '\\x3c': '<', '\\x3e': '>'
            }
            for k, v in map_replace.items():
                s = s.replace(k, v)
            return s

        # 2. 补全标题与描述文本 - 优先尝试 DOM，失败则从 JS 变量全局搜索
        desc_text = ""
        desc_elem = soup.find(id='js_image_desc') or soup.find(class_='js_underline_content')
        if desc_elem:
            desc_text = desc_elem.get_text(separator='\n').strip()
            
        # 如果标题为空，尝试从 JS 变量抓取
        if not title:
            # 简化版 cgiData 匹配，更稳健
            cgi_title = re.search(r'title:\s*JsDecode\([\'\"](.*?)[\'\"]', html_text)
            if cgi_title:
                title = wechat_js_decode(cgi_title.group(1))
            
            # 尝试 msg_title
            if not title:
                msg_title = re.search(r'var\s+msg_title\s*=\s*[\'\"](.*?)[\'\"]', html_text)
                if msg_title:
                    title = wechat_js_decode(msg_title.group(1))
        
        # 提取封面图 URL 以便后续过滤 (去除封面图不要)
        cover_url = ""
        # 常见变量名：msg_cdn_url, share_cover
        cover_match = re.search(r'var\s+msg_cdn_url\s*=\s*["\'](.*?)["\'];', html_text) or \
                      re.search(r'share_cover:\s*{\s*cdn_url:\s*["\'](.*?)["\']', html_text)
        if cover_match:
            cover_url = wechat_js_decode(cover_match.group(1))
        
        # 如果通过变量没找到，尝试在 window.cgiData 中找 msg_cdn_url 或 share_cover
        if not cover_url:
            cgi_cover = re.search(r'msg_cdn_url:\s*JsDecode\([\'\"](.*?)[\'\"]', html_text) or \
                        re.search(r'share_cover:\s*{.*?cdn_url:\s*(?:JsDecode\()?[\'\"](.*?)[\'\"]', html_text, re.DOTALL)
            if cgi_cover:
                cover_url = wechat_js_decode(cgi_cover.group(1))

        # 核心改进：精确匹配主图 (主图 URL 后面一定会跟着 width: 属性)
        img_list = []
        img_matches = re.findall(r"cdn_url:\s*(?:JsDecode\()?['\"](.*?)['\"][\)?]*\s*,\s*width:", html_text)
        for img_url in img_matches:
            decoded_url = wechat_js_decode(img_url)
            # 过滤非微信图片域名
            if not decoded_url or 'mmbiz.qpic.cn' not in decoded_url:
                continue
            
            # 1. 直接匹配封面变量进行过滤
            if cover_url and (cover_url in decoded_url or decoded_url in cover_url):
                print(f"Filtering out cover image (matched cover_url): {decoded_url}")
                continue
            
            # 2. 图片集辅助判断：正文图通常带有 from=appmsg 且不是封面
            # 如果是 jpeg 且没有 from=appmsg，大概率也是封面或冗余图
            if 'wx_fmt=jpeg' in decoded_url and 'from=appmsg' not in decoded_url:
                print(f"Filtering out potential cover image (jpeg without appmsg): {decoded_url}")
                continue
            
            # 去重并加入列表
            if decoded_url not in img_list:
                img_list.append(decoded_url)

        # 如果 DOM 描述为空，尝试从 JS 变量中抓取可能的长描述
        if not desc_text:
            # 搜索 JsDecode 内的长字符串，且不包含 URL
            potential_texts = re.findall(r"JsDecode\(['\"](.*?)['\"]\)", html_text)
            for p in potential_texts:
                decoded = wechat_js_decode(p)
                # 经验：文章描述通常较长 (>100字符)，且包含换行符或特定关键词
                if len(decoded) > 100 and 'http' not in decoded[:50]:
                    if not desc_text or len(decoded) > len(desc_text):
                        desc_text = decoded
        
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
    
    # 在原位置将视频标签转换为可识别的 HTML 格式，同时提取封面图和 VID
    video_count = 0
    video_covers = {}  # 存储视频封面图
    video_ids = {}     # 存储视频 VID
    
    # helper: 解码 URL
    def safe_unquote(u):
        if not u: return ""
        if '&amp;' in u:
            u = u.replace('&amp;', '&')
        return unquote(u)

    # 1. 处理 iframe 视频（腾讯视频、微信视频号等）
    for iframe in article.find_all('iframe'):
        src = safe_unquote(iframe.get('data-src') or iframe.get('src', ''))
        cover = safe_unquote(iframe.get('data-cover') or iframe.get('data-poster') or '')
        
        # 尝试从 src 提取 VID
        vid = ''
        if src:
            vid_match = re.search(r'vid=(wxv_\w+|TX\w+)', src)
            if vid_match:
                vid = vid_match.group(1)
                
        if src and ('v.qq.com' in src or 'mp.weixin.qq.com' in src or 'channels' in src or 'mpvideo' in src):
            video_count += 1
            video_covers[video_count] = cover
            video_ids[video_count] = vid
            new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
            new_tag.string = f'[[VIDEO_WECHAT:{video_count}]]'
            iframe.replace_with(new_tag)
    
    # 2. 处理 mpvideo 标签（微信自有视频标签）
    for mpvideo in article.find_all('mpvideo'):
        src = safe_unquote(mpvideo.get('data-src') or mpvideo.get('src', ''))
        cover = safe_unquote(mpvideo.get('data-cover') or mpvideo.get('cover') or mpvideo.get('data-poster', ''))
        video_id = mpvideo.get('data-vidtype') or mpvideo.get('data-videoid') or mpvideo.get('data-mpvid', '')
        
        if src or cover or video_id:
            video_count += 1
            video_covers[video_count] = cover
            video_ids[video_count] = video_id
            new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
            new_tag.string = f'[[VIDEO_WECHAT:{video_count}]]'
            mpvideo.replace_with(new_tag)
    
    # 3. 处理 wx-video 标签（视频号视频）
    for wxvideo in article.find_all(['wx-video', 'mp-common-videosnap']):
        cover = safe_unquote(wxvideo.get('data-poster') or wxvideo.get('data-cover') or wxvideo.get('data-headimgurl', ''))
        video_id = wxvideo.get('data-id') or wxvideo.get('id', '')
        
        video_count += 1
        video_covers[video_count] = cover
        video_ids[video_count] = video_id
        new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
        new_tag.string = f'[[VIDEO_WECHAT:{video_count}]]'
        wxvideo.replace_with(new_tag)
    
    # 4. 处理标准 video 标签
    for video in article.find_all('video'):
        src = safe_unquote(video.get('data-src') or video.get('src', ''))
        poster = safe_unquote(video.get('poster', ''))
        source = video.find('source')
        if source and not src:
            src = safe_unquote(source.get('src', ''))
            
        # 尝试从 src 提取 VID
        vid = ''
        if src:
            vid_match = re.search(r'vid=(wxv_\w+|TX\w+)', src)
            if vid_match:
                vid = vid_match.group(1)
                
        if src or poster:
            video_count += 1
            video_covers[video_count] = poster
            video_ids[video_count] = vid
            new_tag = soup.new_tag('div', attrs={'class': 'video-embed'})
            new_tag.string = f'[[VIDEO_WECHAT:{video_count}]]'
            video.replace_with(new_tag)
            
    # 移除不需要的标签
    for tag in article(["script", "style", "nav", "footer", "noscript", "header", "aside"]):
        tag.decompose()
    
    # 将视频占位符替换为封面图+链接（类似图片处理方式）
    text = md(str(article), heading_style="ATX")

    def replace_video_placeholder(match):
        placeholder = match.group(0)
        if placeholder.startswith('[[VIDEO_WECHAT:'):
            video_num = int(placeholder[15:-2])
            cover = video_covers.get(video_num, '')
            vid = video_ids.get(video_num, '')
            
            # 1. 尝试获取视频地址并直接播放（不下载）
            if vid and vid.startswith('wxv_'):
                print(f"Attempting to process video {video_num} with VID: {vid}")
                try:
                    mp4_url = _get_wechat_video_url(vid, url)
                    if mp4_url:
                        # 直接使用远程 MP4 地址
                        # 添加 referrerpolicy="no-referrer" 尝试规避防盗链
                        return f'\n\n<video src="{mp4_url}" controls preload="metadata" width="100%" referrerpolicy="no-referrer" style="border-radius: 8px; margin: 10px 0; max-height: 600px;"></video>\n\n'
                except Exception as e:
                    print(f"Error getting video URL: {e}")
            
            # 2. 如果获取失败，回退到封面图逻辑
            
            # 如果有封面图，使用代理显示封面
            cover = safe_unquote(cover)
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
    text = md(str(article), heading_style="ATX")
    text = text.replace('\\_', '_')
    text = re.sub(r'\[\[VIDEO_WECHAT:\d+\]\]', replace_video_placeholder, text)
    
    # 添加底部来源链接
    text = text.strip()
    text += "\n\n---\n"
    if url:
        text += f"*来源: [微信公众号]({url})*\n"
    else:
        text += "*来源: 微信公众号*\n"
    
    # 尝试提取作者/公众号名称
    author = ""
    # 1. DOM 提取
    if soup.find(id='js_name'):
        author = soup.find(id='js_name').get_text().strip()
    elif soup.find(class_='profile_nickname'):
        author = soup.find(class_='profile_nickname').get_text().strip()
    
    # 2. 如果 DOM 没找到，尝试从 JS 变量提取
    if not author:
        # 匹配 var nickname = "..." 
        nickname_match = re.search(r'var\s+nickname\s*=\s*[\'"](.*?)[\'"]', html_text)
        if nickname_match:
            author = nickname_match.group(1)
        
        # 匹配 user_name = "..."
        if not author:
            user_name_match = re.search(r'item_show_type.*?user_name\s*:\s*[\'"](.*?)[\'"]', html_text, re.DOTALL)
            if user_name_match:
                author = user_name_match.group(1)

    # 将作者信息添加到文章开头
    if author:
        text = f"**作者**: {author}\n\n{text}"

    return {
        'title': title,
        'content': text,
        'author': author
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
    
    author = "今日头条作者" # Placeholder or try extract
    # Try extract author
    # <div class="article-meta"> or similar
    # Look for 'author-name' or 'name' common in Toutiao
    meta_author = soup.find(class_='article-sub') or soup.find(class_='name')
    if meta_author:
        author = meta_author.get_text().strip()

    if author and "今日头条作者" not in author:
         text = f"**作者**: {author}\n\n{text}"

    return {
        'title': title,
        'content': text,
        'author': author if "今日头条作者" not in author else "" 
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
            'author': nickname,
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
    
    author = ""
    # Zhihu Author
    # <div class="AuthorInfo-name">...</div>
    author_elem = soup.find(class_='AuthorInfo-name') or soup.find(class_='UserLink-link')
    if author_elem:
        author = author_elem.get_text().strip()
    
    # Prepend author
    if author:
        text = f"**作者**: {author}\n\n{text}"

    return {
        'title': title,
        'content': text,
        'author': author
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
    
    author = ""
    # Try generic author meta
    # <meta name="author" content="...">
    meta_author = soup.find('meta', attrs={'name': 'author'}) or soup.find('meta', property='article:author')
    if meta_author:
        author = meta_author.get('content', '')
    
    if not author:
        # Try common classes
        author_elem = soup.find(class_=re.compile(r'author|byline', re.I))
        if author_elem:
            author = author_elem.get_text().strip()
            
    if author:
         text = f"**作者**: {author}\n\n{text}"

    return {
        'title': title.strip() if title else '',
        'content': text,
        'author': author
    }
