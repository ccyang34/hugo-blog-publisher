#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hugo博客发布器 - Flask后端API
"""

import os
import time
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from .services.deepseek import DeepSeekService
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
    
    deepseek_service = MockDeepSeekService()
    print("Warning: DeepSeek API key not set, using mock service")

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


# Global job store and queue
jobs = {}
task_queue = queue.Queue()


def add_job_log(job_id, step, status, message, details=None):
    """为任务添加详细日志
    
    Args:
        job_id: 任务ID
        step: 步骤名称
        status: 状态 ('start', 'success', 'error', 'warning', 'info')
        message: 日志消息
        details: 额外详情（可选）
    """
    log_entry = {
        'timestamp': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'step': step,
        'status': status,
        'message': message
    }
    if details:
        log_entry['details'] = details
    
    if job_id in jobs:
        if 'logs' not in jobs[job_id]:
            jobs[job_id]['logs'] = []
        jobs[job_id]['logs'].append(log_entry)

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
        target_dir = data.get('target_dir', 'content/posts')
        draft = data.get('draft', False)
        auto_format = data.get('auto_format', True)
        
        add_job_log(job_id, '参数解析', 'success', '参数解析完成', {
            'has_title': bool(title),
            'target_dir': target_dir,
            'draft': draft
        })

        # 1. Check if content is a URL
        url_pattern = re.compile(r'^https?://\S+$')
        is_url = url_pattern.match(content.strip())
        
        if is_url:
            url = content.strip()
            jobs[job_id]['message'] = '正在抓取链接内容...'
            add_job_log(job_id, 'URL抓取', 'start', f'检测到URL，开始抓取内容', {'url': url})
            print(f"Detected URL in publish: {url}, fetching content...")
            
            scraped_data = fetch_article_content(url)
            
            if scraped_data:
                content = scraped_data['content']
                if not title and scraped_data['title']:
                    title = scraped_data['title']
                    print(f"Use scraped title: {title}")
                add_job_log(job_id, 'URL抓取', 'success', '成功获取文章内容', {
                    'url': url,
                    'title': title,
                    'content_length': len(content)
                })
            else:
                add_job_log(job_id, 'URL抓取', 'error', '无法从链接获取内容', {'url': url})
                raise Exception('无法从链接获取内容，请检查链接是否有效')
        else:
            add_job_log(job_id, '内容识别', 'info', '内容为纯文本，无需抓取URL')

        # 2. Parse Front Matter to avoid duplication
        add_job_log(job_id, 'Front Matter解析', 'start', '开始解析Front Matter')
        parsed = markdown_generator.parse_front_matter(content)
        content = parsed['content']
        add_job_log(job_id, 'Front Matter解析', 'success', 'Front Matter解析完成')
        
        # 3. AI Analysis
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
            
            if not title:
                extracted_title = parsed.get('front_matter', {}).get('title')
                title = extracted_title if extracted_title else analysis.get('title', '未命名文章')
            
            add_job_log(job_id, 'AI分析', 'success', 'AI优化排版完成', {
                'title': title,
                'category': category,
                'tags': tags
            })
                
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
            category=category,
            draft=draft
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
                'url': result['url']
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


@app.route('/', methods=['GET'])
def index():
    """主页 - API 测试界面"""
    return render_template('index.html')



@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon():
    """消除 favicon 404 错误"""
    return '', 204


@app.route('/api/format', methods=['POST'])
def format_article():
    """
    调用DeepSeek API进行文章排版
    
    请求参数:
    {
        "content": "原始文章内容",
        "title": "文章标题（可选）",
        "tags": ["标签1", "标签2"]（可选）,
        "category": "分类"（可选）
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
        
        # Check if content is a URL
        # Basic regex for URL: starts with http/https, no spaces, seems like a single link
        url_pattern = re.compile(r'^https?://\S+$')
        if url_pattern.match(content.strip()):
            print(f"Detected URL: {content.strip()}, fetching content...")
            scraped_data = fetch_article_content(content.strip())
            
            if scraped_data:
                content = scraped_data['content']
                # Only use scraped title if user didn't provide one
                if not title and scraped_data['title']:
                    title = scraped_data['title']
                    print(f"Use scraped title: {title}")
            else:
                return jsonify({
                    'success': False,
                    'error': '无法从链接获取内容，请检查链接是否有效'
                }), 400
        
        analysis = deepseek_service.format_article(
            content=content,
            title=title,
            tags=tags,
            category=category
        )
        
        # 整合分析结果
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
    """发布文章到GitHub"""
    try:
        data = request.json
        
        # Validate parameters (Check for content presence)
        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必要参数（content）'
            }), 400
            
        # Create a new job
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            'id': job_id,
            'status': 'queued',
            'created_at': datetime.now().isoformat(),
            'message': '任务已进入队列...',
            'progress': 0,
            'logs': []  # 初始化日志数组
        }
        
        # 记录任务创建日志
        add_job_log(job_id, '任务创建', 'info', '任务已创建并加入队列', {
            'title': data.get('title', ''),
            'target_dir': data.get('target_dir', 'content/posts')
        })
        
        # Add to queue instead of starting thread immediately
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
    job = jobs.get(job_id)
    if not job:
        return jsonify({
            'success': False,
            'error': '任务不存在'
        }), 404
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'status': job.get('status'),
        'logs': job.get('logs', [])
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
        result = github_service.list_files(path, fetch_metadata=fetch_metadata)
        
        if result['success']:
            files = [f for f in result.get('files', []) if f['name'].endswith(('.md', '.markdown'))]
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


@app.route('/api/verify-password', methods=['POST'])
def verify_password():
    """验证发布密码"""
    try:
        data = request.json
        password = data.get('password', '')
        
        correct_password = os.environ.get('PUBLISH_PASSWORD', 'chen')
        
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
            return jsonify({
                'success': True,
                'message': '图片上传成功',
                'url': image_url,
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
