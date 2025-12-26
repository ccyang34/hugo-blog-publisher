#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek API服务
"""

import os
import json
import requests
from typing import List, Optional, Dict, Any


class DeepSeekService:
    """DeepSeek API服务类"""
    
    def __init__(self):
        self.api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        self.base_url = 'https://api.deepseek.com'
        self.model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
        
        if not self.api_key:
            raise ValueError('未设置DeepSeek API密钥，请配置环境变量DEEPSEEK_API_KEY')
    
    def _call_api(self, messages: List[dict], temperature: float = 0.7) -> str:
        """
        调用DeepSeek API
        
        参数:
            messages: 消息列表
            temperature: 温度参数
            
        返回:
            API返回的文本内容
        """
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': 4096
        }
        
        response = requests.post(
            f'{self.base_url}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )
        
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def _build_format_prompt(self, content: str, title: str, tags: List[str], category: str) -> str:
        """
        构建格式化提示词
        
        参数:
            content: 原始文章内容
            title: 文章标题
            tags: 标签列表
            category: 分类
            
        返回:
            完整的提示词
        """
        prompt = f"""你是一个专业的博客文章编辑专家，擅长解析和排版静态网站内容。
请对以下文章内容进行深度分析并重新排版。

## 原始内容
{content}

## 处理要求
1. **内容分析**：
   - 识别文章的核心主题，提取 1 个最合适的分类（Category）。
   - 提取 5-8 个核心标签（Tags）。
   - 如果未提供标题或标题较弱，请生成/优化一个简洁有力的标题。
2. **格式排版**：
   - 修正错别字，优化段落，添加 H2/H3 小标题。
   - 遵循规范的 Markdown 语法。
   - 严禁输出 YAML Front Matter 或 Markdown 一级标题（H1）。
3. **输出格式**：
   - 必须以 JSON 格式返回，包含以下字段：
     - `title`: 建议的标题
     - `category`: 建议的分类
     - `tags`: 标签数组
     - `content`: 格式化后的正文 Markdown

直接返回 JSON 对象，不要包含解释或代码块标记。"""
        return prompt
        return prompt
    
    def format_article(self, content: str, title: str = '', tags: List[str] = None, category: str = '') -> Dict[str, Any]:
        """
        格式化文章并分析元数据
        """
        if not content or content.strip() == '':
            raise ValueError('文章内容不能为空')
        
        prompt = self._build_format_prompt(content, title, tags or [], category)
        
        messages = [
            {
                'role': 'system',
                'content': '你是一个精通文章解析与排版的 AI 助手。请根据要求输出 JSON 格式的分析结果。'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        
        try:
            response = self._call_api(messages, temperature=0.5)
            # 处理可能的 JSON 包裹
            if response.startswith('```json'):
                response = response.replace('```json', '', 1).rsplit('```', 1)[0].strip()
            elif response.startswith('```'):
                response = response.replace('```', '', 1).rsplit('```', 1)[0].strip()
            
            result = json.loads(response)
            return {
                'title': result.get('title', '').strip(),
                'category': result.get('category', '').strip(),
                'tags': result.get('tags', []),
                'content': result.get('content', '').strip()
            }
        except Exception as e:
            print(f"Error calling DeepSeek for format: {e}")
            # 降级处理：仅返回原文内容，保持原有元数据
            return {
                'title': title,
                'category': category,
                'tags': tags or [],
                'content': content
            }
    
    def improve_title(self, content: str, original_title: str = '') -> str:
        """
        优化文章标题
        
        参数:
            content: 文章内容
            original_title: 原始标题
            
        返回:
            优化后的标题
        """
        prompt = f"""根据以下文章内容，提炼一个简洁、准确的中文标题。

文章内容：
{content}

要求：
1. 标题不超过30个字符
2. 能够准确概括文章主题
3. 简洁明了，便于理解

{'原始标题：' + original_title if original_title else ''}

请直接返回优化后的标题，不需要任何解释。"""
        
        messages = [
            {
                'role': 'system',
                'content': '你是一个专业的博客编辑，擅长提炼文章标题。'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        
        try:
            improved_title = self._call_api(messages, temperature=0.3)
            return improved_title.strip()
        except requests.exceptions.RequestException as e:
            raise Exception(f'调用DeepSeek API失败：{str(e)}')
    
    def generate_tags(self, content: str, existing_tags: List[str] = None) -> List[str]:
        """
        根据文章内容生成标签
        
        参数:
            content: 文章内容
            existing_tags: 已有的标签
            
        返回:
            标签列表
        """
        prompt = f"""根据以下文章内容，推荐合适的标签。

文章内容：
{content}

{'已有标签：{", ".join(existing_tags)}' if existing_tags else ''}

要求：
1. 标签应该准确反映文章主题
2. 每个标签应该是常见、易于理解的词汇
3. 建议5-8个标签
4. 以JSON数组格式返回，如：["标签1", "标签2", "标签3"]

请直接返回JSON数组，不要包含任何其他文字。"""
        
        messages = [
            {
                'role': 'system',
                'content': '你是一个专业的博客标签推荐助手。'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        
        try:
            response = self._call_api(messages, temperature=0.3)
            tags = json.loads(response)
            if isinstance(tags, list):
                return [str(tag) for tag in tags]
            return []
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            raise Exception(f'生成标签失败：{str(e)}')
    
    def translate_content(self, content: str, target_language: str = '中文') -> str:
        """
        翻译文章内容
        
        参数:
            content: 要翻译的内容
            target_language: 目标语言
            
        返回:
            翻译后的内容
        """
        prompt = f"""请将以下文章翻译成{target_language}，保持原有的Markdown格式不变。

文章内容：
{content}

要求：
1. 保持Markdown格式不变
2. 翻译准确、流畅
3. 专业术语需要准确翻译
4. 直接返回翻译后的内容，不要包含任何解释。"""
        
        messages = [
            {
                'role': 'system',
                'content': f'你是一个专业的翻译专家，擅长将文章翻译成{target_language}，并保持原有的Markdown格式。'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        
        try:
            translated_content = self._call_api(messages, temperature=0.5)
            return translated_content.strip()
        except requests.exceptions.RequestException as e:
            raise Exception(f'翻译失败：{str(e)}')
    
    def summarize_content(self, content: str, max_length: int = 200) -> str:
        """
        生成文章摘要
        
        参数:
            content: 文章内容
            max_length: 最大长度
            
        返回:
            文章摘要
        """
        prompt = f"""请为以下文章生成一段摘要。

文章内容：
{content}

要求：
1. 摘要长度不超过{max_length}个字符
2. 准确概括文章的核心内容
3. 语言简洁明了
4. 直接返回摘要内容，不要包含任何解释。"""
        
        messages = [
            {
                'role': 'system',
                'content': '你是一个专业的文章摘要生成助手。'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        
        try:
            summary = self._call_api(messages, temperature=0.5)
            return summary.strip()
        except requests.exceptions.RequestException as e:
            raise Exception(f'生成摘要失败：{str(e)}')
