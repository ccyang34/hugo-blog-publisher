#!/usr/bin/env python3
"""
通用网页抓取模块
支持提取文章内容和图片URL
"""

import re
import os
import httpx
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_article_content(url: str) -> Dict:
    """
    抓取网页文章内容
    
    Returns:
        {title, author, content, url}
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        
        # 简单提取标题
        title = ""
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
        
        # 提取正文（简化版，去除HTML标签）
        content = ""
        
        # 尝试提取 article 或 main 标签内容
        for tag in ["article", "main", "div[class*='content']", "div[class*='article']"]:
            match = re.search(f'<{tag}[^>]*>(.*?)</{tag}>', html, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1)
                break
        
        if not content:
            content = html
        
        # 清理HTML标签
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', '\n', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = content.strip()
        
        return {
            "success": True,
            "title": title,
            "content": content[:5000],  # 限制长度
            "url": url,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "url": url,
        }


def fetch_article_content_with_images(url: str) -> Dict:
    """
    抓取网页文章内容和图片URL列表
    
    Returns:
        {title, author, content, images: [{url, alt}], url}
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        base_url = str(resp.url)
        
        # 提取标题
        title = ""
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
        
        # 提取图片
        images = []
        seen_urls = set()
        
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        for match in re.finditer(img_pattern, html, re.IGNORECASE):
            img_url = match.group(1)
            
            # 处理相对URL
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            elif img_url.startswith("/"):
                img_url = urljoin(base_url, img_url)
            
            # 过滤小图标
            if any(skip in img_url.lower() for skip in [
                "avatar", "icon", "emoji", "logo", "badge",
                "data:image/svg", "data:image/gif", "1x1",
            ]):
                continue
            
            clean_url = img_url.split("?")[0]
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
            
            # 提取alt文本
            alt_match = re.search(r'alt=["\']([^"\']*)["\']', match.group(0))
            alt = alt_match.group(1) if alt_match else ""
            
            images.append({"url": img_url, "alt": alt})
        
        # 提取正文
        content = html
        for tag in ["article", "main"]:
            match = re.search(f'<{tag}[^>]*>(.*?)</{tag}>', html, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1)
                break
        
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', '\n', content)
        content = re.sub(r'\n\s*\n', '\n\n', content).strip()
        
        return {
            "success": True,
            "title": title,
            "content": content[:5000],
            "images": images[:20],  # 限制图片数量
            "url": url,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "url": url,
        }


def download_images(image_urls: List[str], save_dir: str, referer: str = None) -> List[Dict]:
    """
    下载图片到本地
    
    Returns:
        [{url, path, filename, success}]
    """
    os.makedirs(save_dir, exist_ok=True)
    results = []
    
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        for i, url in enumerate(image_urls):
            try:
                resp = client.get(url)
                resp.raise_for_status()
                
                ct = resp.headers.get("content-type", "")
                ext = ".jpg"
                if "png" in ct: ext = ".png"
                elif "webp" in ct: ext = ".webp"
                elif "gif" in ct: ext = ".gif"
                
                filename = f"image_{i+1:03d}{ext}"
                filepath = os.path.join(save_dir, filename)
                
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                
                results.append({
                    "url": url,
                    "path": filepath,
                    "filename": filename,
                    "success": True,
                    "size_kb": len(resp.content) // 1024,
                })
                
            except Exception as e:
                results.append({
                    "url": url,
                    "success": False,
                    "error": str(e),
                })
    
    return results


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("用法: python3 web_scraper.py <URL>")
        sys.exit(1)
    
    result = fetch_article_content_with_images(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
