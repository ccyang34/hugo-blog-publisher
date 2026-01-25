#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
今日头条API功能测试脚本
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.toutiao_api import ToutiaoScraper

def test_toutiao_api():
    """测试今日头条API"""
    
    # 测试URL - 使用一个今日头条文章链接
    test_url = "https://m.toutiao.com/is/30slkNRb6cQ/"
    
    print("=" * 60)
    print("今日头条API功能测试")
    print("=" * 60)
    print(f"测试URL: {test_url}")
    print()
    
    # 创建抓取器实例
    scraper = ToutiaoScraper(use_public_key=True)
    
    print("开始抓取文章...")
    result = scraper.fetch_article(test_url)
    
    if result.get('success'):
        print("\n✅ 抓取成功!")
        data = result['data']
        
        print("\n文章信息:")
        print(f"  标题: {data.get('title', 'N/A')}")
        print(f"  作者: {data.get('source', 'N/A') or data.get('name', 'N/A')}")
        print(f"  发布时间: {data.get('publishTime', 'N/A')}")
        print(f"  摘要: {data.get('abstract', 'N/A')[:100]}...")
        
        images = data.get('imageList', [])
        print(f"  图片数量: {len(images)}")
        
        content = data.get('content2', '') or data.get('content', '')
        print(f"  内容长度: {len(content)} 字符")
        
        print("\n测试通过! 今日头条API集成成功。")
        return True
    else:
        print(f"\n❌ 抓取失败: {result.get('message')}")
        print("\n这可能是正常的,因为:")
        print("  1. 测试URL可能已过期")
        print("  2. API端点可能需要更新")
        print("  3. 网络连接问题")
        print("\n请使用真实的今日头条文章URL进行测试。")
        return False

if __name__ == '__main__':
    test_toutiao_api()
