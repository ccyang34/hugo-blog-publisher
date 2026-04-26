#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立运行的文章解析 CLI 工具
可以解析微信公众号、今日头条、小红书、知乎等平台的文章，并输出 Markdown 格式。
"""

import sys
import os
import json
import argparse

# 确保能正确导入同一目录下的依赖
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from web_scraper import fetch_article_content
except ImportError as e:
    print(f"Error importing web_scraper: {e}", file=sys.stderr)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="文章解析工具 (支持微信、头条、小红书、知乎等)")
    parser.add_argument("url", help="要解析的文章或网页的 URL")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出完整解析结果")
    parser.add_argument("--output", "-o", help="将输出保存到文件")
    
    args = parser.parse_args()
    
    print(f"正在解析 URL: {args.url} ...", file=sys.stderr)
    result = fetch_article_content(args.url)
    
    if not result:
        print("解析失败或无法获取内容。", file=sys.stderr)
        sys.exit(1)
        
    if args.json:
        output_data = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        title = result.get('title', '无标题')
        author = result.get('author', '')
        content = result.get('content', '')
        
        output_parts = [
            f"# {title}",
            f"作者: {author}" if author else "",
            "",
            content
        ]
        output_data = "\n".join(output_parts)
        
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_data)
            print(f"解析结果已保存至: {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"写入文件失败: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("\n--- 解析结果 ---\n", file=sys.stderr)
        print(output_data)

if __name__ == "__main__":
    main()
