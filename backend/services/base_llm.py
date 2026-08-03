#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 服务公共基类
"""


class BaseLLMService:
    """DeepSeek / 多模态等 LLM 排版服务的公共逻辑基类"""

    # 预设分类及其定位描述
    PRESET_CATEGORIES = {
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

    def _call_api(self, messages: list, temperature: float = 0.7) -> str:
        """调用 LLM API，由子类实现"""
        raise NotImplementedError

    def _clean_json_response(self, response: str) -> str:
        """清理模型返回中可能包裹的代码块标记，返回纯 JSON 文本"""
        if response.startswith('```json'):
            return response.replace('```json', '', 1).rsplit('```', 1)[0].strip()
        if response.startswith('```'):
            return response.replace('```', '', 1).rsplit('```', 1)[0].strip()
        return response

    def _normalize_format_result(self, result: dict) -> dict:
        """
        规范化 format_article 的返回结果
        兼容 category/categories 单/多字段，以及字符串/列表两种类型
        """
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
