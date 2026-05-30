#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模态大模型服务（支持图片OCR和文章排版）
使用 NVIDIA API 的 stepfun-ai/step-3.7-flash 模型
"""

import os
import json
import base64
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any, Union


class MultimodalService:
    """多模态大模型服务类"""

    IMAGE_MIME_TYPES = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }

    def __init__(self):
        self.api_key = os.environ.get('NVIDIA_API_KEY', '')
        self.base_url = 'https://integrate.api.nvidia.com/v1'
        self.model = os.environ.get('NVIDIA_MODEL', 'stepfun-ai/step-3.7-flash')

        self.PRESET_CATEGORIES = {
            "研究报告": "长篇、深度、结构化的正式报告。",
            "期货分析": "针对大豆、油脂、豆油、棕榈油、基差、榨利等期货品种的产业链分析与行情研判。",
            "市场分析": "针对股票、宏观经济、各行业资金流向（如AI行业资金分析）、市场热点等非期货品种的金融/行情复盘。",
            "ETF投资": "针对各类ETF基金（如宽基、行业、跨境ETF）的申购赎回、走势分析、配置策略。",
            "投资策略": "偏向方法论、配置逻辑、模型工具的使用、避坑指南。",
            "投资理财": "泛理财、公募基金、个人财务规划。",
            "AI与技术": "侧重技术层面：AI工具（如Claude, NotebookLM）应用、编程开发、自动化脚本、量化技术干货、AI Agent（Skills/MCP/RAG/Memory）。",
            "新闻资讯": "宏观新闻事件点评、行业突发新闻。",
            "个人随笔": "生活、运动（乒乓球）、学习方法、随感、认知进化。"
        }

        if not self.api_key:
            raise ValueError('未设置NVIDIA API密钥，请配置环境变量NVIDIA_API_KEY')

    def _encode_image_to_base64(self, image_path: str) -> str:
        """将本地图片编码为 base64 data URL"""
        path = Path(image_path)
        with open(path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
        suffix = path.suffix.lower()
        mime_type = self.IMAGE_MIME_TYPES.get(suffix, 'image/png')
        return f"data:{mime_type};base64,{image_b64}"

    def _call_api(self, messages: List[dict], temperature: float = 0.7, max_tokens: int = 16384) -> str:
        """调用多模态 API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95,
            "stream": False
        }

        response = requests.post(
            f'{self.base_url}/chat/completions',
            headers=headers,
            json=payload,
            timeout=120
        )

        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']

    def _build_image_ocr_prompt(self, image_url: str, task: str = "ocr") -> List[dict]:
        """构建图片OCR提示词"""
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"请识别这张图片中的所有文字内容，{task}。请直接输出识别结果，不要添加解释。"},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]

    def _build_format_prompt(self, content: str, title: str, tags: List[str], category: str, image_urls: List[str] = None) -> List[dict]:
        """构建文章格式化提示词（支持多模态输入）"""
        is_xiaohongshu = 'xhs-slider' in content or '来源: 小红书' in content or '**作者**:' in content

        platform_rules = ""
        if is_xiaohongshu:
            platform_rules = """
## 小红书内容专属规则（必须严格遵守）
1. **保留作者信息**：`**作者**: xxx` 必须保留在顶部。
2. **原文链接在底部**：原文链接只能出现在底部来源标注处（`*来源: [小红书](链接)*`），**不要在顶部添加原文链接**。
3. **保留描述内容**：`## 描述` 下的文字内容必须完整保留，只做格式优化，不要删除或重写。
4. **保留所有图片**：所有 `![图片](url)` 格式的图片必须保留。
5. **保留视频标签**：`<video>` 标签必须完整保留。
6. **保留来源标注**：底部的 `*来源: [小红书](链接)*` 必须保留。
7. **保留 emoji 表情**：原文中的所有 emoji 表情符号必须保留。
"""

        text_prompt = f"""你是一个专业的博客文章编辑专家，擅长解析和排版静态网站内容。
请对以下文章内容进行深度分析并重新排版。**注意：输入的内容可能是直接粘贴的文章文本或从网页抓取的 Markdown**。无论哪种，都请严格遵守以下规则。"""

        if image_urls:
            text_prompt += f"\n\n## 图片内容\n文章中包含 {len(image_urls)} 张图片，请一并分析处理。"
        text_prompt += f"""

## 原始内容
{content}
"""

        if image_urls:
            text_prompt += f"\n\n## 图片URL列表\n"
            for i, url in enumerate(image_urls, 1):
                text_prompt += f"图片{i}: {url}\n"

        text_prompt += f"""
## 处理要求
1. **内容分析**：
   - 识别文章的核心主题，提取 1-3 个最合适的分类（Categories）。
     - **分类规范**：基于以下预设分类的"定位"描述，判断最符合的分类。允许选择多个（最多3个），但这要求文章确实跨越了多个领域且相关性都很强。
{chr(10).join([f"     - {k}：{v}" for k, v in self.PRESET_CATEGORIES.items()])}
     - **自主创建规则**：如果文章内容确实不属于上述任何分类，请根据你的理解自主创建一个最能代表文章主题的、简洁的分类（要求 2-4 个汉字）。
   - 提取 5-8 个核心标签（Tags）。
   - **标题处理**：如果原文没有明确标题，请根据内容**必须**生成一个简洁有力的标题；如果已有标题，请保留或仅做微调。**可以根据原始文章标题或者自主命名的标题，在开头添加一个契合主题的emoji，不强制，有契合才添加。**
2. **格式排版（关键）**：
   - **严格保留原义**：不要重写、摘要或扩写正文内容，保持原文的完整性。
   - **保留结构**：严格还原原文的层级结构（H2/H3）、列表（有序/无序）、引用、代码块。
   - **严禁删除图片/链接**：**必须**保留原文中所有的图片链接 `![alt](url)` 和超链接，位置不能错乱。
   - **严禁删除 HTML 标签**：**必须**保留原文中所有的 HTML 标签（如 `<div>`, `<img>`, `<video>` 等）。
   - **优化阅读体验**：仅进行排版层面的优化，如：
     - 修正标点符号（如中英文标点混用）。
     - 优化段落间距。
     - 修正明显的错别字。
   - **Markdown 规范**：确保输出符合标准 Markdown 语法。
   - 严禁输出 YAML Front Matter 或 Markdown 一级标题（H1）。
{platform_rules}
3. **输出格式**：
   - 必须以 JSON 格式返回，包含以下字段：
     - `title`: 最终确定的标题
     - `categories`: 建议的分类数组（List[str]，最多3个）
     - `tags`: 标签数组
     - `content`: 格式化后的正文 Markdown

直接返回 JSON 对象，不要包含解释或代码块标记。"""

        content_list = [{"type": "text", "text": text_prompt}]

        if image_urls:
            for url in image_urls:
                if url.startswith('data:') or url.startswith('http'):
                    content_list.append({"type": "image_url", "image_url": {"url": url}})

        return [{"role": "user", "content": content_list}]

    def _build_image_analysis_prompt(self, image_url: str, context: str = "") -> List[dict]:
        """构建图片分析提示词（用于理解图表等视觉内容）"""
        context_hint = f"\n\n上下文信息：{context}" if context else ""

        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"请详细分析这张图片的内容，包括：标题、关键数据、图表信息等。{context_hint}"},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]

    def ocr_image(self, image_path: str = None, image_url: str = None) -> str:
        """
        对图片进行 OCR 识别

        参数:
            image_path: 本地图片路径
            image_url: 图片 URL

        返回:
            识别出的文字内容
        """
        if image_path:
            image_data = self._encode_image_to_base64(image_path)
        elif image_url:
            image_data = image_url
        else:
            raise ValueError('必须提供 image_path 或 image_url')

        messages = self._build_image_ocr_prompt(image_data, task="识别所有文字")
        return self._call_api(messages, temperature=0.3, max_tokens=8192)

    def analyze_image(self, image_path: str = None, image_url: str = None, context: str = "") -> str:
        """
        分析图片内容（支持图表、数据等）

        参数:
            image_path: 本地图片路径
            image_url: 图片 URL
            context: 上下文提示

        返回:
            图片分析结果
        """
        if image_path:
            image_data = self._encode_image_to_base64(image_path)
        elif image_url:
            image_data = image_url
        else:
            raise ValueError('必须提供 image_path 或 image_url')

        messages = self._build_image_analysis_prompt(image_data, context)
        return self._call_api(messages, temperature=0.5, max_tokens=16384)

    def format_article(self, content: str, title: str = '', tags: List[str] = None, category: str = '', image_urls: List[str] = None) -> Dict[str, Any]:
        """
        格式化文章并分析元数据（支持多模态输入）

        参数:
            content: 文章内容
            title: 文章标题
            tags: 标签列表
            category: 分类
            image_urls: 图片 URL 列表

        返回:
            包含 title, categories, tags, content 的字典
        """
        if not content or content.strip() == '':
            raise ValueError('文章内容不能为空')

        messages = self._build_format_prompt(content, title, tags or [], category, image_urls)

        try:
            response = self._call_api(messages, temperature=0.5, max_tokens=16384)

            if response.startswith('```json'):
                response = response.replace('```json', '', 1).rsplit('```', 1)[0].strip()
            elif response.startswith('```'):
                response = response.replace('```', '', 1).rsplit('```', 1)[0].strip()

            result = json.loads(response)

            categories = result.get('categories', [])
            if not categories and result.get('category'):
                categories = [result.get('category')]

            if isinstance(categories, str):
                categories = [categories]

            return {
                'title': result.get('title', '').strip(),
                'categories': categories,
                'tags': result.get('tags', []),
                'content': result.get('content', '').strip()
            }
        except Exception as e:
            print(f"Error calling Multimodal API for format: {e}")
            return {
                'title': title,
                'categories': [category] if category else [],
                'tags': tags or [],
                'content': content
            }

    def improve_title(self, content: str, original_title: str = '') -> str:
        """优化文章标题"""
        prompt = f"""请根据以下文章内容，优化或生成一个更吸引人的标题。

文章内容：
{content[:2000]}

{'原始标题：' + original_title if original_title else ''}

请直接输出标题，不要添加解释。"""

        messages = [{"role": "user", "content": prompt}]
        return self._call_api(messages, temperature=0.7, max_tokens=256)

    def extract_text_from_markdown_images(self, markdown_content: str, max_images: int = 10) -> List[Dict[str, str]]:
        """
        从 Markdown 内容中提取图片 URL 列表

        参数:
            markdown_content: Markdown 内容
            max_images: 最大处理图片数量

        返回:
            图片信息列表 [{'url': str, 'alt': str, 'index': int}]
        """
        import re

        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(pattern, markdown_content)

        images = []
        for i, (alt, url) in enumerate(matches[:max_images]):
            images.append({
                'url': url,
                'alt': alt,
                'index': i
            })

        return images