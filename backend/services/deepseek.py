#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek API服务
"""

import os
import json
import requests
from typing import List, Optional


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
        prompt = f"""你是一个专业的博客文章编辑专家，擅长将文章按照Hugo静态网站生成器的Markdown格式进行排版和优化。

请对以下文章进行处理：

## 文章信息
- 标题：{title if title else '待定'}
- 分类：{category if category else '未分类'}
- 标签：{', '.join(tags) if tags else '无'}

## 原始内容
{content}

## 处理要求

1. **标题处理**：
   - 如果原始内容中没有标题，请根据内容提炼一个简洁、准确的中文标题
   - 标题应该简洁明了，不超过50个字符

2. **内容优化**：
   - 修正错别字和语病
   - 优化段落结构，使文章层次分明
   - 适当添加小标题（H2、H3级别）来组织内容
   - 保持原文的核心意思不变

3. **Markdown格式**：
   - 正确使用Markdown语法（标题、列表、引用、代码块等）
   - 中文和英文、数字之间添加空格
   - 代码块需要标注语言类型
   - 列表项使用统一的格式

4. **图片引用**：
   - 文章中的图片请使用标准Markdown格式：![描述](/images/图片文件名)
   - 如果原文中已有图片链接，**保持原样不做修改**
   - 不要在文章内容中嵌入 base64 图片

5. **Hugo兼容性**：
   - 确保内容与Hugo的Markdown渲染器兼容
   - 避免使用特殊的非标准Markdown语法
   - 文章正文中只引用图片路径，不做其他处理

7. **严禁事项**：
   - **绝对不要**包含 YAML Front Matter（即文章开头的 --- 包裹的元数据区域）
   - **绝对不要**包含文章标题作为 Markdown 一级标题（H1），因为标题会通过元数据单独处理
   - 只返回文章正文内容

## 输出格式
请直接返回处理后的 Markdown 格式文章正文，**不要包含 YAML 头部元数据**，不要包含任何解释性文字或 markdown 代码块标记。

文章内容："""
        return prompt
    
    def format_article(self, content: str, title: str = '', tags: List[str] = None, category: str = '') -> str:
        """
        格式化文章
        
        参数:
            content: 原始文章内容
            title: 文章标题
            tags: 标签列表
            category: 分类
            
        返回:
            格式化后的Markdown内容
        """
        if not content or content.strip() == '':
            raise ValueError('文章内容不能为空')
        
        tags = tags or []
        
        prompt = self._build_format_prompt(content, title, tags, category)
        
        messages = [
            {
                'role': 'system',
                'content': '你是一个专业的博客文章编辑专家，精通各种静态网站生成器的Markdown格式要求，特别是Hugo。你排版的文章格式规范、内容优化得当、层次分明。'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        
        try:
            formatted_content = self._call_api(messages, temperature=0.5)
            return formatted_content.strip()
        except requests.exceptions.RequestException as e:
            raise Exception(f'调用DeepSeek API失败：{str(e)}')
    
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
