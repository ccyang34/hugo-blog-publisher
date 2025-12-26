#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown格式处理工具
"""

import re
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
import unicodedata


class MarkdownGenerator:
    """Markdown格式处理类"""
    
    def __init__(self):
        self.default_category = '未分类'
        self.default_tags = []
    
    def slugify(self, text: str) -> str:
        """
        将文本转换为URL友好的slug
        
        参数:
            text: 输入文本
            
        返回:
            slug格式的字符串
        """
        if not text:
            return ''
        
        text = str(text).strip()
        
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        
        text = text.lower()
        
        text = re.sub(r'[^\w\s-]', '', text)
        
        text = re.sub(r'[\s_-]+', '-', text)
        
        text = re.sub(r'^-+|-+$', '', text)
        
        return text[:100]
    
    def generate_filename(self, title: str, date: Optional[str] = None) -> str:
        """
        生成Hugo文章文件名
        
        Hugo文件名格式: YYYY-MM-DD-title-slug.md
        
        参数:
            title: 文章标题
            date: 日期字符串，格式为YYYY-MM-DD
            
        返回:
            文件名
        """
        # 确保文件名只使用日期部分 (YYYY-MM-DD)
        date_part = date[:10] if date else datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
        
        slug = self.slugify(title)
        
        if not slug:
            slug = 'post'
        
        return f'{date_part}-{slug}.md'
    
    def generate_front_matter(self, title: str, date: Optional[str] = None,
                             tags: Optional[List[str]] = None,
                             category: Optional[str] = None,
                             content: str = '') -> str:
        """
        生成Hugo文章front matter
        
        参数:
            title: 文章标题
            date: 日期
            tags: 标签列表
            category: 分类
            content: 文章内容（可选，用于生成摘要）
            
        返回:
            front matter字符串
        """
        if not date:
            date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S+08:00')
        
        if tags is None:
            tags = []
        
        if not category:
            category = self.default_category
        
        front_matter_lines = ['---']
        front_matter_lines.append(f'title: "{self._escape_yaml_string(title)}"')
        front_matter_lines.append(f'date: "{date}"')
        
        if category:
            front_matter_lines.append(f'categories: [{self._escape_yaml_string(category)}]')
        
        if tags:
            tags_str = ', '.join([self._escape_yaml_string(tag) for tag in tags])
            front_matter_lines.append(f'tags: [{tags_str}]')
        
        front_matter_lines.append('---')
        
        return '\n'.join(front_matter_lines)
    
    def wrap_with_front_matter(self, title: str, content: str,
                               date: Optional[str] = None,
                               tags: Optional[List[str]] = None,
                               category: Optional[str] = None,
                               draft: bool = False,
                               featured_image: str = '') -> str:
        """
        将文章内容包装为完整的Hugo Markdown格式
        
        参数:
            title: 文章标题
            content: 文章内容（Markdown格式）
            date: 日期
            tags: 标签列表
            category: 分类
            draft: 是否为草稿
            featured_image: 特色图片
            
        返回:
            完整的Hugo文章内容
        """
        if not date:
            date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S+08:00')
        
        if tags is None:
            tags = []
        
        if not category:
            category = self.default_category
        
        lines = ['---']
        lines.append(f'title: "{self._escape_yaml_string(title)}"')
        lines.append(f'date: "{date}"')
        
        if draft:
            lines.append('draft: true')
        
        if category:
            lines.append(f'categories: [{self._escape_yaml_string(category)}]')
        
        if tags:
            tags_str = ', '.join([self._escape_yaml_string(tag) for tag in tags])
            lines.append(f'tags: [{tags_str}]')
        
        if featured_image:
            lines.append(f'featuredImage: "{featured_image}"')
            lines.append(f'image: "{featured_image}"')
        
        lines.append('---')
        lines.append('')
        lines.append(content)
        
        return '\n'.join(lines)
    
    def _escape_yaml_string(self, text: str) -> str:
        """
        转义YAML字符串中的特殊字符
        
        参数:
            text: 原始字符串
            
        返回:
            转义后的字符串
        """
        if not text:
            return ''
        
        text = str(text)
        
        if '"' in text or ':' in text or '{' in text or '}' in text:
            return text.replace('"', '\\"')
        
        return text
    
    def parse_front_matter(self, markdown_content: str) -> Dict[str, Any]:
        """
        解析Markdown文件中的front matter
        
        参数:
            markdown_content: Markdown内容
            
        返回:
            包含front matter和内容的字典
        """
        if not markdown_content.startswith('---'):
            return {
                'front_matter': {},
                'content': markdown_content
            }
        
        lines = markdown_content.split('\n')
        
        if len(lines) < 3:
            return {
                'front_matter': {},
                'content': markdown_content
            }
        
        front_matter_lines = []
        content_start_index = 0
        
        for i, line in enumerate(lines):
            if line == '---':
                if front_matter_lines:
                    content_start_index = i + 1
                    break
                else:
                    front_matter_lines.append(i)
        
        front_matter_text = '\n'.join(lines[1:content_start_index - 1])
        
        content = '\n'.join(lines[content_start_index:])
        
        front_matter = self._parse_yaml(front_matter_text)
        
        return {
            'front_matter': front_matter,
            'content': content
        }
    
    def _parse_yaml(self, yaml_text: str) -> Dict[str, Any]:
        """
        简单的YAML解析
        
        参数:
            yaml_text: YAML文本
            
        返回:
            解析后的字典
        """
        result = {}
        
        for line in yaml_text.strip().split('\n'):
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            if ':' not in line:
                continue
            
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            if value.startswith('[') and value.endswith(']'):
                value = self._parse_yaml_list(value)
            elif value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            elif value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.lower() == 'null':
                value = None
            else:
                value = value
            
            result[key] = value
        
        return result
    
    def _parse_yaml_list(self, list_str: str) -> List[str]:
        """
        解析YAML列表
        
        参数:
            list_str: 列表字符串，如 [item1, item2]
            
        返回:
            字符串列表
        """
        list_str = list_str.strip()
        
        if not (list_str.startswith('[') and list_str.endswith(']')):
            return []
        
        inner = list_str[1:-1]
        
        if not inner.strip():
            return []
        
        items = []
        current_item = ''
        in_string = False
        string_char = None
        
        for char in inner:
            if char in ('"', "'") and not in_string:
                in_string = True
                string_char = char
                current_item += char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
                current_item += char
            elif char == ',' and not in_string:
                items.append(current_item.strip())
                current_item = ''
            else:
                current_item += char
        
        if current_item.strip():
            items.append(current_item.strip())
        
        return [item.strip().strip('"\'') for item in items if item.strip()]
    
    def validate_markdown(self, content: str) -> Dict[str, Any]:
        """
        验证Markdown内容的有效性
        
        参数:
            content: Markdown内容
            
        返回:
            验证结果
        """
        issues = []
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            if line.startswith('#') and not re.match(r'^#{1,6}\s', line):
                issues.append(f'第{i}行: 标题格式不正确，应为 # 标题')
            
            if line.count('**') % 2 != 0:
                issues.append(f'第{i}行: 粗体标记不匹配')
            
            if line.count('*') % 2 != 0 and '**' not in line:
                issues.append(f'第{i}行: 斜体标记不匹配')
            
            if line.count('`') % 2 != 0 and line.count('```') % 2 == 0:
                issues.append(f'第{i}行: 代码标记不匹配')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'line_count': len(lines),
            'word_count': len(content.split())
        }
    
    def extract_toc(self, content: str, max_level: int = 3) -> List[Dict[str, Any]]:
        """
        从Markdown内容中提取目录
        
        参数:
            content: Markdown内容
            max_level: 最大标题级别
            
        返回:
            目录列表
        """
        toc = []
        
        for line in content.split('\n'):
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if match:
                level = len(match.group(1))
                
                if level <= max_level:
                    toc.append({
                        'level': level,
                        'title': match.group(2).strip(),
                        'slug': self.slugify(match.group(2))
                    })
        
        return toc
    
    def word_count(self, content: str) -> int:
        """
        统计文章字数
        
        参数:
            content: Markdown内容
            
        返回:
            字数
        """
        text = re.sub(r'```[\s\S]*?```', '', content)
        text = re.sub(r'`[^`]+`', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'[#*_~\[\]()]/g', '', text)
        text = re.sub(r'\s+', ' ', text)
        
        words = text.strip().split()
        
        return len(words)
    
    def reading_time(self, content: str, words_per_minute: int = 200) -> int:
        """
        计算阅读时间
        
        参数:
            content: Markdown内容
            words_per_minute: 每分钟阅读字数
            
        返回:
            阅读时间（分钟）
        """
        words = self.word_count(content)
        
        minutes = words / words_per_minute
        
        return max(1, int(minutes))
