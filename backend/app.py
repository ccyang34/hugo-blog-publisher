#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hugo博客发布器 - Flask后端API
"""

import os
import time
import json
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from .services.deepseek import DeepSeekService
from .services.multimodal import MultimodalService
from .services.github import GitHubService

from .utils.markdown import MarkdownGenerator
from .utils.web_scraper import fetch_article_content
from .utils.web_scraper import fetch_article_content
import re
import threading
import uuid
import traceback
import queue
import atexit

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app, origins=[os.environ.get('FRONTEND_URL', '*')])

try:
    deepseek_service = DeepSeekService()
except ValueError:
    # 如果DeepSeek API密钥未设置，创建一个模拟服务
    class MockDeepSeekService:
        def format_markdown(self, content):
            return content + "\n\n<!-- 由于DeepSeek API密钥未设置，未进行格式优化 -->"
        
        def format_article(self, content, title='', tags=None, category=''):
            """模拟格式化接口，返回原始数据附件简单的降级信息"""
            return {
                'title': title or f"未命名文章_{datetime.now(timezone(timedelta(hours=8))).strftime('%m%d%H%M')}",
                'categories': [category] if category else ["未分类"],
                'tags': tags or ["待分类"],
                'content': content + "\n\n<!-- Mock Mode: DeepSeek API Key not set -->"
            }
    
    deepseek_service = MockDeepSeekService()
    print("Warning: DeepSeek API key not set, using mock service")

multimodal_service = None
try:
    multimodal_service = MultimodalService()
    print("MultimodalService initialized successfully (NVIDIA API)")
except ValueError as e:
    print(f"Warning: MultimodalService not initialized: {e}")
    print("Hint: Set NVIDIA_API_KEY environment variable to enable image OCR and multimodal features")
except Exception as e:
    print(f"Warning: MultimodalService initialization failed: {e}")

try:
    github_service = GitHubService()
except ValueError:
    github_service = None
    print("Warning: GitHub credentials not set, GitHub functionality disabled")

try:
    markdown_generator = MarkdownGenerator()
except ValueError:
    markdown_generator = None
    print("Warning: Markdown generator not initialized, some functionality may be disabled")

# QStash 客户端初始化
qstash_client = None
qstash_receiver = None
QSTASH_TOKEN = os.environ.get('QSTASH_TOKEN', '')
QSTASH_SIGNING_KEY = os.environ.get('QSTASH_CURRENT_SIGNING_KEY', '')

if QSTASH_TOKEN:
    try:
        from qstash import QStash
        from qstash import Receiver as QStashReceiver
        qstash_client = QStash(token=QSTASH_TOKEN)
        if QSTASH_SIGNING_KEY:
            qstash_receiver = QStashReceiver(
                current_signing_key=QSTASH_SIGNING_KEY,
                next_signing_key=os.environ.get('QSTASH_NEXT_SIGNING_KEY', QSTASH_SIGNING_KEY)
            )
        print("QStash client initialized successfully")
    except Exception as e:
        print(f"Warning: QStash initialization failed: {e}")
else:
    print("Warning: QSTASH_TOKEN not set, async task functionality disabled")

# Upstash Redis 初始化（用于存储任务历史）
redis_client = None
UPSTASH_REDIS_URL = os.environ.get('UPSTASH_REDIS_REST_URL', '')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_REST_TOKEN', '')

if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
    try:
        from upstash_redis import Redis
        redis_client = Redis(url=UPSTASH_REDIS_URL, token=UPSTASH_REDIS_TOKEN)
        print("Upstash Redis initialized successfully")
    except Exception as e:
        print(f"Warning: Redis initialization failed: {e}")
else:
    print("Warning: UPSTASH_REDIS not configured, task history will use localStorage only")

TASK_HISTORY_KEY = "hugo_publisher:task_history"
MAX_TASK_HISTORY = 20


def save_task_to_history(task_data):
    """保存任务到 Redis 历史记录（如果已存在相同ID则更新，否则新增）"""
    if not redis_client:
        return False
    try:
        task_id = task_data.get('id')
        history = redis_client.lrange(TASK_HISTORY_KEY, 0, -1) or []
        
        # 检查是否已存在相同 ID 的任务
        for i, item in enumerate(history):
            existing_task = json.loads(item) if isinstance(item, str) else item
            if existing_task.get('id') == task_id:
                # 找到已存在的任务，更新它（保留原始创建时间）
                if 'created_at' not in task_data and 'created_at' in existing_task:
                    task_data['created_at'] = existing_task['created_at']
                redis_client.lset(TASK_HISTORY_KEY, i, json.dumps(task_data))
                print(f"[Redis] Updated existing task {task_id}")
                return True
        
        # 不存在，添加新任务到列表头部
        redis_client.lpush(TASK_HISTORY_KEY, json.dumps(task_data))
        
        # 只保留最近 MAX_TASK_HISTORY 条
        redis_client.ltrim(TASK_HISTORY_KEY, 0, MAX_TASK_HISTORY - 1)
        print(f"[Redis] Added new task {task_id}")
        return True
    except Exception as e:
        print(f"Error saving task to history: {e}")
        return False


def get_task_history():
    """获取任务历史记录"""
    if not redis_client:
        return []
    try:
        history = redis_client.lrange(TASK_HISTORY_KEY, 0, MAX_TASK_HISTORY - 1) or []
        return [json.loads(item) if isinstance(item, str) else item for item in history]
    except Exception as e:
        print(f"Error getting task history: {e}")
        return []


def update_task_history_title(job_id, title):
    """更新任务历史中的标题（处理过程中获取到标题后调用）"""
    if not redis_client or not job_id or not title:
        return False
    try:
        history = redis_client.lrange(TASK_HISTORY_KEY, 0, -1) or []
        for i, item in enumerate(history):
            task = json.loads(item) if isinstance(item, str) else item
            if task.get('id') == job_id:
                # 找到匹配的任务，更新标题
                task['title'] = title
                redis_client.lset(TASK_HISTORY_KEY, i, json.dumps(task))
                print(f"[Redis] Updated task {job_id} title to: {title[:30]}...")
                return True
        return False
    except Exception as e:
        print(f"Error updating task history title: {e}")
        return False


# Global job store and queue
jobs = {}
task_queue = queue.Queue()


def add_job_log(job_id, step, status, message, details=None):
    """为任务添加详细日志"""
    log_entry = {
        'timestamp': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'step': step,
        'status': status,
        'message': message
    }
    if details:
        log_entry['details'] = details
    
    # 1. Save to in-memory store (for current instance)
    if job_id in jobs:
        if 'logs' not in jobs[job_id]:
            jobs[job_id]['logs'] = []
        jobs[job_id]['logs'].append(log_entry)
        
    # 2. Save to Redis (for persistence)
    if redis_client:
        try:
            log_key = f"hugo_publisher:logs:{job_id}"
            redis_client.rpush(log_key, json.dumps(log_entry))
            # Set expiry (e.g., 24 hours)
            redis_client.expire(log_key, 86400) 
        except Exception as e:
            print(f"Failed to save log to Redis: {e}")

def get_job_logs_from_redis(job_id):
    """从 Redis 获取任务日志"""
    if not redis_client:
        return []
    try:
        log_key = f"hugo_publisher:logs:{job_id}"
        logs = redis_client.lrange(log_key, 0, -1) or []
        return [json.loads(log) if isinstance(log, str) else log for log in logs]
    except Exception as e:
        print(f"Failed to get logs from Redis: {e}")
        return []

def worker():
    """Background worker to process the queue - 任务失败时跳过继续处理下一个"""
    while True:
        job_id = None
        try:
            job_id, data = task_queue.get()
            if job_id is None:  # Sentinel to stop worker
                break
            
            try:
                process_publish_task(job_id, data, deepseek_service, github_service, markdown_generator)
            except Exception as e:
                # 任务处理失败，记录错误但继续处理下一个任务
                print(f"Task {job_id} failed with exception: {e}")
                traceback.print_exc()
                if job_id and job_id in jobs:
                    jobs[job_id]['status'] = 'failed'
                    jobs[job_id]['error'] = f'任务处理异常: {str(e)}'
                    add_job_log(job_id, '任务异常', 'error', f'任务处理异常: {str(e)}')
            finally:
                # 无论成功还是失败，都标记任务完成以释放队列
                task_queue.task_done()
                
        except Exception as e:
            print(f"Worker queue exception: {e}")
            traceback.print_exc()
            # 确保即使获取任务出错也标记完成
            if job_id is not None:
                task_queue.task_done()

# Start worker thread
worker_thread = threading.Thread(target=worker, daemon=True)
worker_thread.start()


def process_publish_task(job_id, data, deepseek_service, github_service, markdown_generator):
    """
    Background task to process article publishing
    """
    try:
        # Update status to processing
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['message'] = '正在分析文章内容...'
        jobs[job_id]['progress'] = 10
        add_job_log(job_id, '开始处理', 'start', '任务开始处理')
        
        title = data.get('title', '').strip()
        content = data['content']
        date = data.get('date', datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S+08:00'))
        tags = data.get('tags', [])
        category = data.get('category', '')
        categories = [] # Initialize categories list
        author = data.get('author', '')
        target_dir = data.get('target_dir', 'content/posts')
        draft = data.get('draft', False)
        auto_format = data.get('auto_format', True)
        
        add_job_log(job_id, '参数解析', 'success', '参数解析完成', {
            'has_title': bool(title),
            'target_dir': target_dir,
            'draft': draft
        })

        # 1. 识别 URL（支持从文案中提取）
        url_pattern = re.compile(r'https?://[^\s\u4e00-\u9fa5]+')
        urls = url_pattern.findall(content.strip())
        
        is_xiaohongshu = False
        scraped_data = None
        
        if urls:
            url = urls[0].rstrip('.,!?;:)]}）〉》」』')
            # 小红书链接特殊处理
            if 'xiaohongshu.com' in url or 'xhslink.com' in url:
                is_xiaohongshu = True
                add_job_log(job_id, '小红书识别', 'info', '识别为小红书链接，启用专用解析')
            
            jobs[job_id]['message'] = '正在抓取链接内容...'
            add_job_log(job_id, 'URL抓取', 'start', f'检测到URL，开始抓取内容', {'url': url})
            print(f"Detected URL in publish: {url}, fetching content...")
            
            scraped_data = fetch_article_content(url)
            
            if scraped_data:
                content = scraped_data['content']
                if not title and scraped_data.get('title'):
                    title = scraped_data['title']
                    print(f"Use scraped title: {title}")
                
                if not author and scraped_data.get('author'):
                    author = scraped_data['author']
                    print(f"Use scraped author: {author}")
                # 检查是否需要跳过 AI 排版（纯图片笔记）
                skip_ai_format = scraped_data.get('skip_ai_format', False)
                add_job_log(job_id, 'URL抓取', 'success', '成功获取文章内容', {
                    'url': url,
                    'title': title,
                    'content_length': len(content),
                    'platform': 'xiaohongshu' if is_xiaohongshu else 'generic',
                    'skip_ai_format': skip_ai_format
                })
                # 立即更新任务历史中的标题
                if title:
                    update_task_history_title(job_id, title)
            else:
                add_job_log(job_id, 'URL抓取', 'error', '无法从链接获取内容', {'url': url})
                raise Exception('无法从链接获取内容，请检查链接是否有效')
        else:
            add_job_log(job_id, '内容识别', 'info', '内容为纯文本，无需抓取URL')
            skip_ai_format = False

        # 2. Parse Front Matter to avoid duplication
        add_job_log(job_id, 'Front Matter解析', 'start', '开始解析Front Matter')
        parsed = markdown_generator.parse_front_matter(content)
        content = parsed['content']
        add_job_log(job_id, 'Front Matter解析', 'success', 'Front Matter解析完成')
        
        # 3. AI Analysis（纯图片笔记跳过）
        if skip_ai_format:
            add_job_log(job_id, 'AI分析', 'info', '纯图片笔记，跳过AI排版')
            # 保持原始内容，只设置基本分类和标签
            if not category:
                category = 'AI绘画' if is_xiaohongshu else '未分类'
            if not tags:
                tags = ['小红书', '图集']
        else:
            jobs[job_id]['message'] = '正在进行AI优化排版...'
            jobs[job_id]['progress'] = 30
            add_job_log(job_id, 'AI分析', 'start', '开始AI优化排版')
            
            try:
                analysis = deepseek_service.format_article(
                    content=content,
                    title=title,
                    tags=tags,
                    category=category
                )
                
                content = analysis.get('content', content)
                tags = analysis.get('tags', [])
                category = analysis.get('category', '未分类')
                categories = analysis.get('categories', [])
                # 如果没有返回多分类，则使用单分类
                if not categories and category:
                    categories = [category]
                
                if not title:
                    extracted_title = parsed.get('front_matter', {}).get('title')
                    title = extracted_title if extracted_title else analysis.get('title', '未命名文章')
                
                add_job_log(job_id, 'AI分析', 'success', 'AI优化排版完成', {
                    'title': title,
                    'categories': categories,
                    'tags': tags
                })
                # AI分析完成后，更新任务历史中的标题（对于粘贴文本无标题的情况）
                if title:
                    update_task_history_title(job_id, title)
                    
            except Exception as e:
                print(f"Warning: AI analysis failed: {e}")
                add_job_log(job_id, 'AI分析', 'warning', f'AI分析失败，使用默认值: {str(e)}')
                if not title:
                    title = f"未命名文章_{datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d%H%M%S')}"

        # 4. Generate full content
        jobs[job_id]['message'] = '正在生成文件...'
        jobs[job_id]['progress'] = 60
        add_job_log(job_id, '生成文件', 'start', '开始生成Markdown文件')
        
        filename = markdown_generator.generate_filename(title)
        full_content = markdown_generator.wrap_with_front_matter(
            title=title,
            content=content,
            date=date,
            tags=tags,
            category=category, # Legacy compatibility
            categories=categories, # New multi-category support
            draft=draft,
            author=author
        )
        
        add_job_log(job_id, '生成文件', 'success', '文件生成完成', {
            'filename': filename,
            'content_length': len(full_content)
        })
        
        # 5. Upload to GitHub
        jobs[job_id]['message'] = '正在上传到GitHub...'
        jobs[job_id]['progress'] = 80
        add_job_log(job_id, 'GitHub上传', 'start', '开始上传到GitHub', {
            'filename': filename,
            'target_dir': target_dir
        })
        
        result = github_service.upload_file(
            content=full_content,
            filename=filename,
            target_dir=target_dir,
            message=f'Publish: {title}'
        )
        
        if result['success']:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['progress'] = 100
            jobs[job_id]['message'] = '文章发布成功'
            jobs[job_id]['result'] = {
                'file_path': result['file_path'],
                'url': result['url'],
                'title': title  # Include final title for task history
            }
            add_job_log(job_id, 'GitHub上传', 'success', '文章发布成功', {
                'file_path': result['file_path'],
                'url': result['url']
            })
            add_job_log(job_id, '任务完成', 'success', '发布流程全部完成')
        else:
            add_job_log(job_id, 'GitHub上传', 'error', '上传失败', {'error': result.get('error', '上传失败')})
            raise Exception(result.get('error', '上传失败'))
            
    except Exception as e:
        print(f"Job {job_id} failed: {str(e)}")
        traceback.print_exc()
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)
        add_job_log(job_id, '任务失败', 'error', f'任务执行失败: {str(e)}')


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    # 获取北京时间 (UTC+8)
    beijing_time = datetime.now(timezone(timedelta(hours=8)))
    return jsonify({
        'status': 'ok',
        'timestamp': beijing_time.isoformat()
    })


@app.route('/api/test-deepseek', methods=['GET'])
def test_deepseek():
    """测试 DeepSeek API 连接状态"""
    beijing_time = datetime.now(timezone(timedelta(hours=8)))
    
    # 检查是否是真实的 DeepSeekService 而不是 MockDeepSeekService
    is_mock = not hasattr(deepseek_service, '_call_api')
    api_key_set = bool(os.environ.get('DEEPSEEK_API_KEY', ''))
    
    if is_mock:
        return jsonify({
            'success': False,
            'error': 'DeepSeek API Key 未配置，当前使用 Mock 服务',
            'api_key_set': api_key_set,
            'mode': 'mock',
            'timestamp': beijing_time.isoformat()
        }), 500
    
    try:
        # 直接调用一次简单的 DeepSeek API
        messages = [
            {'role': 'system', 'content': '你是一个助手，请用JSON格式回答。'},
            {'role': 'user', 'content': '请返回这个JSON：{"status": "ok", "message": "DeepSeek API 连接正常"}'}
        ]
        raw_response = deepseek_service._call_api(messages, temperature=0.1)
        
        return jsonify({
            'success': True,
            'message': 'DeepSeek API 连接正常',
            'api_key_set': True,
            'mode': 'real',
            'model': deepseek_service.model,
            'raw_response': raw_response[:200],
            'timestamp': beijing_time.isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'api_key_set': api_key_set,
            'mode': 'real',
            'model': getattr(deepseek_service, 'model', 'unknown'),
            'timestamp': beijing_time.isoformat()
        }), 500


@app.route('/api/test-multimodal', methods=['GET'])
def test_multimodal():
    """测试多模态大模型 API 连接状态"""
    beijing_time = datetime.now(timezone(timedelta(hours=8)))

    if not multimodal_service:
        return jsonify({
            'success': False,
            'error': '多模态服务未配置',
            'hint': '请设置 NVIDIA_API_KEY 环境变量',
            'timestamp': beijing_time.isoformat()
        }), 500

    return jsonify({
        'success': True,
        'message': '多模态服务已配置',
        'model': multimodal_service.model,
        'timestamp': beijing_time.isoformat()
    })


@app.route('/api/ocr-image', methods=['POST'])
def ocr_image():
    """
    对图片进行 OCR 识别（使用多模态大模型）

    请求参数 (JSON):
        image_url: 图片 URL
        image_data: base64 编码的图片数据（可选，与 image_url 二选一）

    返回:
        OCR 识别结果
    """
    beijing_time = datetime.now(timezone(timedelta(hours=8)))

    if not multimodal_service:
        return jsonify({
            'success': False,
            'error': '多模态服务未配置，请设置 NVIDIA_API_KEY 环境变量'
        }), 500

    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400

        image_url = data.get('image_url')
        image_data = data.get('image_data')

        if not image_url and not image_data:
            return jsonify({'success': False, 'error': '必须提供 image_url 或 image_data'}), 400

        result = multimodal_service.ocr_image(image_url=image_url, image_path=None)
        if image_data:
            result = multimodal_service.ocr_image(image_url=image_data)

        return jsonify({
            'success': True,
            'result': result,
            'timestamp': beijing_time.isoformat()
        })

    except Exception as e:
        print(f"OCR error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analyze-image', methods=['POST'])
def analyze_image():
    """
    分析图片内容（使用多模态大模型）

    请求参数 (JSON):
        image_url: 图片 URL
        context: 上下文提示（可选）

    返回:
        图片分析结果
    """
    beijing_time = datetime.now(timezone(timedelta(hours=8)))

    if not multimodal_service:
        return jsonify({
            'success': False,
            'error': '多模态服务未配置，请设置 NVIDIA_API_KEY 环境变量'
        }), 500

    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400

        image_url = data.get('image_url')
        context = data.get('context', '')

        if not image_url:
            return jsonify({'success': False, 'error': '必须提供 image_url'}), 400

        result = multimodal_service.analyze_image(image_url=image_url, context=context)

        return jsonify({
            'success': True,
            'result': result,
            'timestamp': beijing_time.isoformat()
        })

    except Exception as e:
        print(f"Image analysis error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/format-with-images', methods=['POST'])
def format_with_images():
    """
    使用多模态大模型进行文章排版（支持图片OCR）

    请求参数 (JSON):
        content: 文章内容
        title: 文章标题（可选）
        tags: 标签列表（可选）
        category: 分类（可选）
        image_urls: 图片 URL 列表（可选）

    返回:
        格式化后的文章
    """
    beijing_time = datetime.now(timezone(timedelta(hours=8)))

    if not multimodal_service:
        return jsonify({
            'success': False,
            'error': '多模态服务未配置，请设置 NVIDIA_API_KEY 环境变量'
        }), 500

    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400

        content = data.get('content', '')
        title = data.get('title', '')
        tags = data.get('tags', [])
        category = data.get('category', '')
        image_urls = data.get('image_urls', [])

        if not content:
            return jsonify({'success': False, 'error': '文章内容不能为空'}), 400

        result = multimodal_service.format_article(
            content=content,
            title=title,
            tags=tags,
            category=category,
            image_urls=image_urls
        )

        return jsonify({
            'success': True,
            'result': result,
            'timestamp': beijing_time.isoformat()
        })

    except Exception as e:
        print(f"Format with images error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/test-github', methods=['GET'])
def test_github():
    """测试 GitHub API 连接状态"""
    beijing_time = datetime.now(timezone(timedelta(hours=8)))
    
    if not github_service:
        return jsonify({
            'success': False,
            'error': 'GitHub 服务未配置',
            'timestamp': beijing_time.isoformat()
        }), 500
    
    try:
        # 调用 GitHub 服务的验证方法
        result = github_service.validate_config()
        
        if result.get('valid'):
            repo_info = result.get('repo', {})
            return jsonify({
                'success': True,
                'message': 'GitHub API 连接正常',
                'repo': {
                    'name': repo_info.get('name', ''),
                    'full_name': repo_info.get('full_name', ''),
                    'default_branch': repo_info.get('default_branch', 'main'),
                    'url': repo_info.get('url', '')
                },
                'timestamp': beijing_time.isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '验证失败'),
                'timestamp': beijing_time.isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': beijing_time.isoformat()
        }), 500


@app.route('/api/github-status', methods=['GET'])
def get_github_status():
    """获取 GitHub Actions 最新运行状态"""
    if not github_service:
        return jsonify({
            'success': False,
            'error': 'GitHub 服务未设置'
        }), 500
    
    try:
        result = github_service.get_latest_workflow_run()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/test-qstash', methods=['GET'])
def test_qstash():
    """测试 QStash 配置状态"""
    beijing_time = datetime.now(timezone(timedelta(hours=8)))
    
    qstash_status = {
        'success': True,
        'qstash_enabled': qstash_client is not None,
        'qstash_token_set': bool(QSTASH_TOKEN),
        'qstash_signing_key_set': bool(QSTASH_SIGNING_KEY),
        'webhook_base_url': os.environ.get('WEBHOOK_BASE_URL', '未设置'),
        'timestamp': beijing_time.isoformat()
    }
    
    if not QSTASH_TOKEN:
        qstash_status['success'] = False
        qstash_status['error'] = 'QSTASH_TOKEN 未设置，异步模式不可用'
    elif not qstash_client:
        qstash_status['success'] = False
        qstash_status['error'] = 'QStash 客户端初始化失败'
    else:
        qstash_status['message'] = 'QStash 配置正常，异步模式可用'
    
    return jsonify(qstash_status)


@app.route('/', methods=['GET'])
def index():
    """主页 - API 测试界面"""
    return render_template('index.html')


@app.route('/api/task-history', methods=['GET', 'DELETE'])
def api_get_task_history():
    """获取或清除任务历史记录"""
    if request.method == 'DELETE':
        # 清除所有历史记录
        try:
            if redis_client:
                redis_client.delete(TASK_HISTORY_KEY)
                return jsonify({'success': True, 'message': '历史记录已清除'})
            else:
                return jsonify({'success': False, 'error': 'Redis 未配置'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET 请求
    try:
        history = get_task_history()
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/task-history', methods=['POST'])
def api_save_task_history():
    """保存任务到历史记录（供前端调用）"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '缺少任务数据'}), 400
        
        # 添加时间戳
        if 'created_at' not in data:
            data['created_at'] = datetime.now(timezone(timedelta(hours=8))).isoformat()
        
        success = save_task_to_history(data)
        return jsonify({
            'success': success,
            'message': '任务已保存' if success else 'Redis 未配置，无法保存'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon():
    """消除 favicon 404 错误"""
    return '', 204


@app.route('/api/format', methods=['POST'])
def format_article():
    """
    调用大模型进行文章排版
    - enable_ocr=False: 使用 DeepSeek API 进行排版
    - enable_ocr=True: 使用多模态大模型（stepfun-ai/step-3.7-flash）进行排版，能识别图片内容

    请求参数:
    {
        "content": "原始文章内容",
        "title": "文章标题（可选）",
        "tags": ["标签1", "标签2"]（可选）,
        "category": "分类"（可选）,
        "enable_ocr": true/false（可选，默认false）
    }
    """
    try:
        data = request.json

        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': '缺少文章内容'
            }), 400

        content = data['content']
        title = data.get('title', '')
        tags = data.get('tags', [])
        category = data.get('category', '')
        enable_ocr = data.get('enable_ocr', False)

        url_pattern = re.compile(r'https?://[^\s\u4e00-\u9fa5]+')
        urls = url_pattern.findall(content.strip())
        image_urls = []

        if urls:
            url = urls[0].rstrip('.,!?;:)]}）〉》」』')
            print(f"Detected URL: {url}, fetching content...")
            scraped_data = fetch_article_content(url)

            if scraped_data:
                content = scraped_data['content']
                if not title and scraped_data.get('title'):
                    title = scraped_data['title']
                    print(f"Use scraped title: {title}")

                if enable_ocr and scraped_data.get('platform') == 'xiaohongshu':
                    image_urls = scraped_data.get('image_urls', [])

        if enable_ocr and multimodal_service:
            print(f"[Multimodal] Using stepfun model for article formatting with {len(image_urls)} images...")
            analysis = multimodal_service.format_article(
                content=content,
                title=title,
                tags=tags,
                category=category,
                image_urls=image_urls
            )
            print(f"[Multimodal] Formatting complete")
        else:
            print(f"[DeepSeek] Using DeepSeek for article formatting...")
            analysis = deepseek_service.format_article(
                content=content,
                title=title,
                tags=tags,
                category=category
            )

        formatted_content = analysis.get('content', '')
        suggested_title = analysis.get('title', title) if not title else title
        suggested_category = analysis.get('category', category)
        suggested_tags = analysis.get('tags', tags)

        return jsonify({
            'success': True,
            'formatted_content': formatted_content,
            'suggested_title': suggested_title,
            'suggested_category': suggested_category,
            'suggested_tags': suggested_tags
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/preview', methods=['POST'])
def preview_article():
    """
    生成文章预览（仅生成front matter）
    
    请求参数:
    {
        "title": "文章标题",
        "date": "2024-12-25"（可选，默认当前时间）,
        "tags": ["标签1", "标签2"]（可选）,
        "category": "分类"（可选）,
        "content": "文章内容"
    }
    """
    try:
        data = request.json
        
        if not data or 'title' not in data:
            return jsonify({
                'success': False,
                'error': '缺少文章标题'
            }), 400
        
        title = data['title']
        content = data.get('content', '')
        date = data.get('date', datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S+08:00'))
        tags = data.get('tags', [])
        category = data.get('category', '')
        
        front_matter = markdown_generator.generate_front_matter(
            title=title,
            date=date,
            tags=tags,
            category=category,
            content=content
        )
        
        return jsonify({
            'success': True,
            'front_matter': front_matter
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/publish', methods=['POST'])
def publish_article():
    """发布文章到GitHub
    
    支持两种模式：
    - sync=true: 同步模式，直接在请求中完成发布（推荐用于 Serverless）
    - sync=false 或不传: 异步模式，使用后台队列处理
    """
    try:
        data = request.json
        
        # Validate parameters (Check for content presence)
        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必要参数（content）'
            }), 400
        
        # 检查发布模式
        # async_mode=true: 使用 QStash 异步（推荐，提交后立即返回）
        # sync=true: 同步模式（等待完成）
        async_mode = data.get('async', False)
        sync_mode = data.get('sync', True)
        
        if async_mode and qstash_client:
            # QStash 异步模式：通过 QStash 发送任务，立即返回
            job_id = str(uuid.uuid4())
            
            # 获取当前请求的基础 URL 来构建 webhook URL
            base_url = os.environ.get('WEBHOOK_BASE_URL', request.host_url.rstrip('/'))
            webhook_url = f"{base_url}/api/qstash-webhook"
            
            try:
                # 准备发送给 QStash 的数据
                task_data = {
                    'job_id': job_id,
                    'title': data.get('title', ''),
                    'content': data['content'],
                    'tags': data.get('tags', []),
                    'category': data.get('category', ''),
                    'target_dir': data.get('target_dir', 'content/posts'),
                    'draft': data.get('draft', False)
                }
                
                # 通过 QStash 发布任务
                qstash_client.message.publish_json(
                    url=webhook_url,
                    body=task_data,
                    retries=3
                )
                
                return jsonify({
                    'success': True,
                    'message': '任务已提交到后台处理',
                    'job_id': job_id,
                    'mode': 'async'
                })
                
            except Exception as e:
                print(f"QStash publish error: {e}")
                # 如果 QStash 失败，回退到同步模式
                return publish_sync(data)
        
        elif sync_mode:
            # 同步模式：直接在当前请求中完成发布
            return publish_sync(data)
        else:
            # 旧的后台队列模式（在 Serverless 环境中可能不可靠）
            job_id = str(uuid.uuid4())
            jobs[job_id] = {
                'id': job_id,
                'status': 'queued',
                'created_at': datetime.now().isoformat(),
                'message': '任务已进入队列...',
                'progress': 0,
                'logs': []
            }
            
            add_job_log(job_id, '任务创建', 'info', '任务已创建并加入队列', {
                'title': data.get('title', ''),
                'target_dir': data.get('target_dir', 'content/posts')
            })
            
            task_queue.put((job_id, data))
            
            return jsonify({
                'success': True,
                'message': '任务已加入队列',
                'job_id': job_id,
                'queue_position': task_queue.qsize()
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def publish_sync(data):
    """同步发布文章 - 直接在当前请求中完成所有步骤"""
    try:
        title = data.get('title', '').strip()
        content = data['content']
        date = data.get('date', datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S+08:00'))
        tags = data.get('tags', [])
        category = data.get('category', '')
        target_dir = data.get('target_dir', 'content/posts')
        draft = data.get('draft', False)

        # 1. 识别 URL（支持从文案中提取）
        url_pattern = re.compile(r'https?://[^\s\u4e00-\u9fa5]+')
        urls = url_pattern.findall(content.strip())
        
        is_xiaohongshu = False
        
        if urls:
            url = urls[0].rstrip('.,!?;:)]}）〉》」』')
            # 小红书链接特殊处理
            if 'xiaohongshu.com' in url or 'xhslink.com' in url:
                is_xiaohongshu = True
                print(f"[Sync] Detected Xiaohongshu URL: {url}")
            
            print(f"[Sync] Detected URL: {url}, fetching content...")
            scraped_data = fetch_article_content(url)
            
            if scraped_data:
                content = scraped_data['content']
                if not title and scraped_data.get('title'):
                    title = scraped_data['title']
                    print(f"[Sync] Use scraped title: {title}")
            else:
                return jsonify({
                    'success': False,
                    'error': '无法从链接获取内容，请检查链接是否有效'
                }), 400

        # 2. Parse Front Matter to avoid duplication
        parsed = markdown_generator.parse_front_matter(content)
        content = parsed['content']
        
        # 3. AI Analysis
        try:
            analysis = deepseek_service.format_article(
                content=content,
                title=title,
                tags=tags,
                category=category
            )
            
            content = analysis.get('content', content)
            tags = analysis.get('tags', [])
            category = analysis.get('category', '未分类')
            
            if not title:
                extracted_title = parsed.get('front_matter', {}).get('title')
                title = extracted_title if extracted_title else analysis.get('title', '未命名文章')
                
        except Exception as e:
            print(f"[Sync] Warning: AI analysis failed: {e}")
            if not title:
                # 尝试从 front matter 获取，如果没有则生成带时间戳的标题
                extracted_title = parsed.get('front_matter', {}).get('title')
                title = extracted_title if extracted_title else f"未命名文章_{datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d%H%M%S')}"
            if not category: category = "未分类"
            if not tags: tags = ["未分类"]

        # 4. Generate full content
        filename = markdown_generator.generate_filename(title)
        full_content = markdown_generator.wrap_with_front_matter(
            title=title,
            content=content,
            date=date,
            tags=tags,
            category=category,
            draft=draft
        )
        
        # 5. Upload to GitHub
        result = github_service.upload_file(
            content=full_content,
            filename=filename,
            target_dir=target_dir,
            message=f'Publish: {title}'
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': '文章发布成功',
                'file_path': result['file_path'],
                'url': result['url'],
                'title': title
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '上传失败')
            }), 500
            
    except Exception as e:
        print(f"[Sync] Publish failed: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/qstash-webhook', methods=['POST'])
def qstash_webhook():
    """QStash Webhook 端点 - 接收异步任务并执行发布"""
    # 验证 QStash 签名（可选但推荐）
    if qstash_receiver:
        try:
            signature = request.headers.get('Upstash-Signature', '')
            body = request.get_data(as_text=True)
            qstash_receiver.verify(
                signature=signature,
                body=body,
                url=request.url
            )
        except Exception as e:
            print(f"QStash signature verification failed: {e}")
            return jsonify({'error': 'Invalid signature'}), 401
    
    try:
        data = request.json
        job_id = data.get('job_id', str(uuid.uuid4()))
        
        print(f"[QStash] Received task {job_id}")
        
        # Initialize job entry (critical for process_publish_task)
        jobs[job_id] = {
            'id': job_id,
            'status': 'processing',
            'created_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'progress': 0,
            'logs': []
        }
        
        # Execute publishing via standard processor
        try:
            # Reusing the robust processor which handles fetching, analysis, uploading AND LOGGING
            process_publish_task(job_id, data, deepseek_service, github_service, markdown_generator)
            
            # Check result from jobs dict
            job_result = jobs.get(job_id)
            if job_result and job_result.get('status') == 'completed':
                result_data = job_result.get('result', {})
                print(f"[QStash] Task {job_id} completed via processor")
                
                # Save to history
                save_task_to_history({
                    'id': job_id,
                    'title': result_data.get('title', data.get('title', '未命名')), # Fallback title
                    'status': 'completed',
                    'progress': 100,
                    'message': '发布成功',
                    'file_path': result_data.get('file_path'),
                    'url': result_data.get('url'),
                    'created_at': job_result['created_at']
                })
                
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    'file_path': result_data.get('file_path'),
                    'url': result_data.get('url')
                })
            else:
                 error_msg = job_result.get('error', 'Unknown error') if job_result else 'Job lost'
                 print(f"[QStash] Task {job_id} failed via processor: {error_msg}")
                 return jsonify({'success': False, 'error': error_msg}), 500

        except Exception as inner_e:
            print(f"[QStash] Processor error: {inner_e}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(inner_e)}), 500
            
    except Exception as e:
        print(f"[QStash] Webhook error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """获取任务状态"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({
            'success': False,
            'error': '任务不存在'
        }), 404
        
    return jsonify({
        'success': True,
        'job': job
    })


@app.route('/api/jobs', methods=['GET'])
def get_all_jobs():
    """获取所有任务状态"""
    # Sort jobs by created_at descending (newest first)
    sorted_jobs = sorted(
        jobs.values(),
        key=lambda x: x.get('created_at', ''),
        reverse=True
    )
    
    # Return queue size info too
    return jsonify({
        'success': True,
        'jobs': sorted_jobs,
        'queue_size': task_queue.qsize(),
        'total_jobs': len(jobs)
    })


@app.route('/api/logs/<job_id>', methods=['GET'])
def get_job_logs(job_id):
    """获取任务的详细日志"""
    # 1. Try local memory first
    job = jobs.get(job_id)
    logs = job.get('logs', []) if job else []
    status = job.get('status') if job else 'unknown'
    
    # 2. If no logs locally or job not found, try Redis
    if not logs:
        redis_logs = get_job_logs_from_redis(job_id)
        if redis_logs:
            logs = redis_logs
            # Try to infer status from last log or history
            status = 'completed' # simple hook, or check history
            
    if not logs and not job:
        return jsonify({
            'success': False,
            'error': '无日志记录'
        }), 404
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'status': status,
        'logs': logs
    })


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取当前配置"""
    return jsonify({
        'success': True,
        'config': {
            'default_target_dir': 'content/posts',
            'supported_formats': ['md', 'markdown'],
            'max_content_size': 50 * 1024 * 1024
        }
    })


@app.route('/api/files', methods=['GET'])
def list_files():
    """获取指定目录的文件列表"""
    try:
        path = request.args.get('path', 'content/posts')
        fetch_metadata = request.args.get('fetch_metadata', 'false').lower() == 'true'
        browser_mode = request.args.get('browser', 'false').lower() == 'true'
        recursive = request.args.get('recursive', 'false').lower() == 'true'
        
        # 图片目录默认递归
        if 'images' in path.lower() and not browser_mode:
            recursive = True
            
        result = github_service.list_files(path, fetch_metadata=fetch_metadata, recursive=recursive)
        
        if result['success']:
            all_files = result.get('files', [])
            
            # 浏览器模式：返回所有文件和文件夹
            if browser_mode or path.startswith('static'):
                files = all_files
            elif 'images' in path.lower():
                # 图片目录：保留常见图片格式
                image_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp')
                files = [f for f in all_files if f['name'].lower().endswith(image_exts)]
            else:
                # 默认（文章目录）：保留 Markdown
                files = [f for f in all_files if f['name'].lower().endswith(('.md', '.markdown'))]
            return jsonify({
                'success': True,
                'path': path,
                'files': files
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '获取文件列表失败')
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/file', methods=['GET', 'DELETE'])
def get_file():
    """获取或删除文件内容"""
    try:
        if request.method == 'DELETE':
            path = request.args.get('path', '')
            if not path:
                return jsonify({
                    'success': False,
                    'error': '缺少文件路径'
                }), 400
            
            result = github_service.delete_file(
                path=path,
                message=f'Delete: {path}'
            )
            return jsonify(result)
        else:
            path = request.args.get('path', '')
            if not path:
                return jsonify({
                    'success': False,
                    'error': '缺少文件路径'
                }), 400
            
            result = github_service.get_file_content(path)
            return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/rename', methods=['POST'])
def rename_file():
    """重命名文件或文件夹"""
    try:
        data = request.json
        old_path = data.get('old_path', '')
        new_name = data.get('new_name', '')
        
        if not old_path or not new_name:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400
        
        # 构造新路径
        parts = old_path.rsplit('/', 1)
        if len(parts) == 2:
            new_path = f"{parts[0]}/{new_name}"
        else:
            new_path = new_name
        
        # 获取原文件内容
        original = github_service.get_file_content(old_path)
        if not original.get('success'):
            return jsonify({
                'success': False,
                'error': '无法获取原文件'
            }), 400
        
        # 创建新文件（使用原文件内容）
        import base64
        content_decoded = original.get('content', '')
        
        create_result = github_service.create_or_update_file(
            path=new_path,
            content=content_decoded,
            message=f'Rename: {old_path} -> {new_path}'
        )
        
        if not create_result.get('success'):
            return jsonify({
                'success': False,
                'error': '创建新文件失败'
            }), 500
        
        # 删除原文件
        delete_result = github_service.delete_file(
            path=old_path,
            message=f'Delete old file after rename: {old_path}'
        )
        
        return jsonify({
            'success': True,
            'new_path': new_path
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/verify-password', methods=['POST'])
def verify_password():
    """验证发布密码"""
    try:
        data = request.json
        password = data.get('password', '')
        
        correct_password = os.environ.get('PUBLISH_PASSWORD', 'c')
        
        # 调试日志：输出比对信息（生产环境建议排查后删除）
        print(f"DEBUG: Comparing passwords.")
        print(f"DEBUG: Received: '{password}' (len: {len(password)})")
        print(f"DEBUG: Expected: '{correct_password}' (len: {len(correct_password)})")
        
        if password == correct_password:
            return jsonify({
                'success': True,
                'message': '密码验证成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '密码错误'
            }), 401
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/images/<filename>')
def serve_image(filename):
    """提供图片预览"""
    from flask import send_from_directory
    return send_from_directory(os.path.join(app.root_path, 'static/images'), filename)


@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    """
    上传图片到 GitHub 仓库的 static/images/ 目录
    
    请求参数 (multipart/form-data):
        - file: 图片文件
        - custom_name: 自定义文件名（可选）
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400
        
        file = request.files['file']
        custom_name = request.form.get('custom_name', '')
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400
        
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'}
        filename = file.filename.lower()
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
        
        if ext not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': '不支持的文件格式'
            }), 400
        
        import base64
        image_content = file.read()
        encoded_content = base64.b64encode(image_content).decode('utf-8')
        
        if custom_name:
            safe_name = custom_name.strip()
            if not safe_name.lower().endswith(f'.{ext}'):
                safe_name = f'{safe_name}.{ext}'
        else:
            timestamp = int(time.time())
            safe_name = f'{timestamp}-{filename}'
        
        safe_name = safe_name.replace(' ', '-').replace('_', '-')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '.-_-')
        
        result = github_service.upload_file(
            content=encoded_content,
            filename=safe_name,
            target_dir='static/images',
            message=f'Upload image: {safe_name}',
            is_binary=True
        )
        
        if result['success']:
            image_url = f'/images/{safe_name}'
            # 增加 GitHub Raw URL 作为回退
            # switch to jsdelivr cdn
            raw_url = f"https://cdn.jsdelivr.net/gh/{github_service.username}/{github_service.repo}@main/static/images/{safe_name}"
            return jsonify({
                'success': True,
                'message': '图片上传成功',
                'url': image_url,
                'raw_url': raw_url,
                'filename': safe_name
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '上传失败')
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/delete-image', methods=['POST'])
def delete_image():
    """
    删除已上传的图片
    
    请求参数 (JSON):
        - filename: 图片文件名
    """
    try:
        data = request.json
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': '未提供文件名'
            }), 400
            
        # 安全检查：防止目录遍历
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({
                'success': False,
                'error': '非法的文件名'
            }), 400
            
        target_path = f'static/images/{filename}'
        
        result = github_service.delete_file(
            path=target_path,
            message=f'Delete image: {filename}'
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': '图片删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '删除失败')
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

@app.route('/api/github/workflows', methods=['GET'])
def list_github_workflows():
    """获取所有 Workflows"""
    result = github_service.list_workflows()
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@app.route('/api/github/runs', methods=['GET'])
def list_github_runs():
    """获取最近 Runs"""
    limit = request.args.get('limit', 5)
    workflow_id = request.args.get('workflow_id')
    result = github_service.list_workflow_runs(limit=limit, workflow_id=workflow_id)
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@app.route('/api/github/trigger', methods=['POST'])
def trigger_github_workflow():
    """触发 Workflow"""
    data = request.json
    workflow_id = data.get('workflow_id')
    ref = data.get('ref', 'main')
    
    if not workflow_id:
        return jsonify({'success': False, 'error': 'Missing workflow_id'}), 400
        
    result = github_service.trigger_workflow(workflow_id, ref)
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500


# ============ 视频解析 API ============

@app.route('/api/video/parse', methods=['POST'])
def parse_video():
    """
    解析今日头条视频链接
    
    请求参数:
    {
        "url": "https://m.toutiao.com/is/xxx/"
    }
    
    返回:
    {
        "success": true,
        "data": {
            "video_id": "视频ID",
            "title": "视频标题",
            "cover": "封面图URL",
            "author": "作者",
            "videos": [
                {"quality": "720p", "url": "视频地址"},
                {"quality": "480p", "url": "视频地址"}
            ]
        }
    }
    """
    try:
        from .utils.toutiao_video_api import ToutiaoVideoParser
        
        data = request.json
        
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': '缺少视频URL参数'
            }), 400
        
        url = data['url'].strip()
        
        if not url:
            return jsonify({
                'success': False,
                'error': '视频URL不能为空'
            }), 400
        
        parser = ToutiaoVideoParser()
        
        # 检查是否为支持的链接
        if not parser.is_supported_url(url):
            return jsonify({
                'success': False,
                'error': '不支持的视频链接，目前仅支持今日头条和西瓜视频'
            }), 400
        
        result = parser.parse_video(url)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except ImportError as e:
        return jsonify({
            'success': False,
            'error': f'视频解析模块未安装: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'视频解析失败: {str(e)}'
        }), 500


@app.route('/api/video/info', methods=['GET'])
def get_video_info():
    """
    获取视频信息（GET 方式，方便测试）
    
    参数: ?url=https://m.toutiao.com/is/xxx/
    """
    try:
        from .utils.toutiao_video_api import ToutiaoVideoParser
        
        url = request.args.get('url', '').strip()
        
        if not url:
            return jsonify({
                'success': False,
                'error': '缺少url参数'
            }), 400
        
        parser = ToutiaoVideoParser()
        result = parser.parse_video(url)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
