import requests
from bs4 import BeautifulSoup
import re

def fetch_article_content(url):
    """
    Fetch and extract main content from a URL.
    Returns a dictionary with 'title' and 'content', or None on failure.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Determine encoding if possible, else default to utf-8 or apparent_encoding
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
            script.decompose()
            
        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string
        
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text().strip()
            
        # Extract content - Primitive heuristic: find the container with the most p tags or longest text
        # Better: look for <article>, <main>, or div with class containing 'content', 'article', 'post'
        
        article = soup.find('article')
        if not article:
            article = soup.find('main')
            
        if not article:
            # Fallback: specific common classes
            potential_classes = ['post-content', 'article-content', 'entry-content', 'content', 'main']
            for cls in potential_classes:
                article = soup.find(class_=re.compile(cls, re.I))
                if article:
                    break
        
        if not article:
            # Fallback: body
            article = soup.body
            
        if not article:
            return None

        # Clean up text
        lines = (line.strip() for line in article.get_text().splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n\n'.join(chunk for chunk in chunks if chunk)
        
        return {
            'title': title.strip() if title else "",
            'content': text
        }

    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None
