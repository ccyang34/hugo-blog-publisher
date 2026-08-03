#!/usr/bin/env python3
"""
文章解析 CLI
支持多平台文章提取 + 可选OCR

用法：
    python3 article_parser_cli.py <URL> [--with-ocr] [-o output.md]
"""

import sys
import os
import re
import json
import argparse
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.web_scraper import fetch_article_content_with_images, download_images
from src.ocr_utils import macos_ocr, ocr_image_batch


def is_xhs_url(url: str) -> bool:
    """判断是否是小红书链接"""
    return "xiaohongshu.com" in url or "xhslink" in url


def is_weixin_url(url: str) -> bool:
    """判断是否是微信公众号链接"""
    return "mp.weixin.qq.com" in url


def is_toutiao_url(url: str) -> bool:
    """判断是否是今日头条链接"""
    return "toutiao.com" in url


def is_zhihu_url(url: str) -> bool:
    """判断是否是知乎链接"""
    return "zhihu.com" in url


def generate_markdown(title: str, content: str, ocr_results: list = None, images: list = None, url: str = "") -> str:
    """生成Markdown文章"""
    lines = [
        f"# {title}\n",
        f"**来源**: {url}  ",
        f"**提取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "---\n",
    ]
    
    # 正文
    if content:
        lines.append("## 正文\n")
        for para in [p.strip() for p in content.split("\n") if p.strip()]:
            lines.append(f"{para}\n")
    
    # OCR结果
    if ocr_results:
        text_results = [r for r in ocr_results if r.get("has_text")]
        if text_results:
            lines.append("\n---\n")
            lines.append("## 图片中的文字\n")
            lines.append("*以下文字由 OCR 自动识别*\n")
            
            for r in text_results:
                lines.append(f"### {r['filename']}\n")
                for para in [p.strip() for p in r["text"].split("\n") if p.strip()]:
                    lines.append(f"{para}\n")
                lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="文章解析工具")
    parser.add_argument("url", help="文章URL")
    parser.add_argument("--with-ocr", action="store_true", help="启用OCR识别图片文字")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("--output-dir", default="parsed_articles", help="输出目录")
    parser.add_argument("--download-images", action="store_true", help="下载图片")
    
    args = parser.parse_args()
    url = args.url
    
    print("=" * 60)
    print("📄 文章解析工具")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"OCR: {'启用' if args.with_ocr else '禁用'}")
    print()
    
    # 小红书用专用脚本（路径通过环境变量 XHS_OCR_SCRIPT 配置，未设置时回退通用解析器）
    if is_xhs_url(url):
        xhs_script = os.environ.get("XHS_OCR_SCRIPT", "").strip()
        if xhs_script:
            xhs_script = os.path.expanduser(xhs_script)
            if os.path.isfile(xhs_script):
                print("🔍 检测到小红书链接，使用专用解析器...")
                os.system(f'python3 "{xhs_script}" "{url}"')
                return
            else:
                print(f"⚠️ XHS_OCR_SCRIPT 指向的脚本不存在（{xhs_script}），使用通用解析器")
        else:
            print("⚠️ 未配置 XHS_OCR_SCRIPT，小红书链接将使用通用解析器")
    
    # 通用解析
    print("📥 抓取文章内容...")
    result = fetch_article_content_with_images(url)
    
    if not result.get("success"):
        print(f"❌ 抓取失败: {result.get('error')}")
        sys.exit(1)
    
    title = result.get("title", "未知标题")
    content = result.get("content", "")
    images = result.get("images", [])
    
    print(f"  ✅ 标题: {title}")
    print(f"  ✅ 正文: {len(content)} 字")
    print(f"  ✅ 图片: {len(images)} 张")
    
    # OCR处理
    ocr_results = []
    if args.with_ocr and images:
        print(f"\n🤖 OCR识别图片...")
        
        # 下载图片
        output_dir = args.output_dir
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
        image_dir = os.path.join(output_dir, safe_title, "images")
        
        print(f"  📥 下载 {len(images)} 张图片...")
        downloaded = download_images([img["url"] for img in images], image_dir, referer=url)
        
        successful = [d for d in downloaded if d.get("success")]
        print(f"  ✅ 成功下载 {len(successful)} 张")
        
        # OCR
        if successful:
            print(f"  🔍 OCR识别中...")
            ocr_results = ocr_image_batch([d["path"] for d in successful])
            
            text_count = sum(1 for r in ocr_results if r["has_text"])
            total_chars = sum(r["char_count"] for r in ocr_results if r["has_text"])
            print(f"  ✅ {text_count}张有文字，共{total_chars}字")
    
    # 生成Markdown
    md_content = generate_markdown(title, content, ocr_results, images, url)
    
    # 输出
    if args.output:
        output_path = args.output
    else:
        output_dir = args.output_dir
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
        os.makedirs(os.path.join(output_dir, safe_title), exist_ok=True)
        output_path = os.path.join(output_dir, safe_title, f"{safe_title}.md")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"\n📄 已保存: {output_path}")
    print(f"  正文: {len(content)} 字")
    if ocr_results:
        total_ocr = sum(r["char_count"] for r in ocr_results if r["has_text"])
        print(f"  OCR: {total_ocr} 字")
    print("=" * 60)


if __name__ == "__main__":
    main()
