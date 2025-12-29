import requests
from bs4 import BeautifulSoup
import re
import json
from markdownify import markdownify as md
from urllib.parse import urlparse

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
        
        # Requests with timeout
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        # Handle encoding
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        domain = urlparse(url).netloc
        
        if 'weixin.qq.com' in domain:
            return _handle_wechat(soup)
        elif 'toutiao.com' in domain:
            return _handle_toutiao(soup)
        elif 'xiaohongshu.com' in domain:
            return _handle_xiaohongshu(soup, response.text)
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

def _handle_xiaohongshu(soup, html_text):
    """Parse Xiaohongshu notes"""
    title = ""
    content = ""
    
    # Method 1: Meta tags (most reliable for simple scraping without JS execution)
    og_title = soup.find('meta', property='og:title')
    if og_title:
        title = og_title.get('content', '')
        
    og_desc = soup.find('meta', property='og:description')
    desc = ""
    if og_desc:
        desc = og_desc.get('content', '')
    
    # Extract images from meta tags if possible, or try to parse JSON state
    image_md = ""
    og_image = soup.find('meta', property='og:image')
    if og_image:
        img_url = og_image.get('content', '')
        image_md = f"![{title}]({img_url})\n\n"
        
    if not title and not desc:
         # Try to find JSON state
        try:
            json_pattern = re.search(r'window\.__INITIAL_STATE__=(.*?);', html_text)
            if json_pattern:
                data = json.loads(json_pattern.group(1))
                # This path is hypothetical and needs verification on actual XHS page behavior
                # But typically note data is deeply nested.
                pass
        except:
            pass

    content = f"{image_md}{desc}"
    
    if not content.strip():
        # Fallback to generic, might find something
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
