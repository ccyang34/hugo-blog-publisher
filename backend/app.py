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
import re

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


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    # 获取北京时间 (UTC+8)
    beijing_time = datetime.now(timezone(timedelta(hours=8)))
    return jsonify({
        'status': 'ok',
        'timestamp': beijing_time.isoformat()
    })


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
    """
    发布文章到GitHub
    
    请求参数:
    {
        "title": "文章标题",
        "content": "文章内容（Markdown格式）",
        "date": "2024-12-25"（可选，默认当前时间）,
        "tags": ["标签1", "标签2"]（可选）,
        "category": "分类"（可选）,
        "target_dir": "content/posts"（可选，默认content/posts）,
        "draft": false（可选，默认false）
    }
    """
    try:
        data = request.json
        
        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必要参数（content）'
            }), 400
        
        title = data.get('title', '').strip()
        content = data['content']
        date = data.get('date', datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S+08:00'))
        tags = data.get('tags', [])
        category = data.get('category', '')
        target_dir = data.get('target_dir', 'content/posts')
        draft = data.get('draft', False)
        auto_format = data.get('auto_format', True)  # 默认自动优化排版
        
        # 1. Check if content is a URL (Same logic as format_article)
        url_pattern = re.compile(r'^https?://\S+$')
        if url_pattern.match(content.strip()):
            print(f"Detected URL in publish: {content.strip()}, fetching content...")
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

        # 2. 清除内容中可能已存在的 Front Matter 头部，防止重复
        parsed = markdown_generator.parse_front_matter(content)
        content = parsed['content']
        
        # 2. 调用 DeepSeek 优化排版并分析元数据 (分类、标签、标题)
        # 即使 auto_format=False，为了获取分类标签也需要分析，除非系统有其他策略
        # 我们这里默认发布时都会通过 AI 进行分类标签提取
        try:
            analysis = deepseek_service.format_article(
                content=content,
                title=title,
                tags=tags,
                category=category
            )
            
            # 正文使用优化后的内容
            content = analysis.get('content', content)
            
            # 分类和标签强制使用 AI 生成的结果
            tags = analysis.get('tags', [])
            category = analysis.get('category', '未分类')
            
            # 标题逻辑：如果用户没填，则使用 AI 建议的标题
            if not title:
                # 尝试从原本剥离的头部中找标题（如果存在）
                extracted_title = parsed.get('front_matter', {}).get('title')
                title = extracted_title if extracted_title else analysis.get('title', '未命名文章')
                
        except Exception as e:
            print(f"Warning: AI analysis failed: {e}")
            # 失败时回退：如果没有标题，给个默认的
            if not title:
                title = f"未命名文章_{datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d%H%M%S')}"

        # 3. 生成文件名和完整的 Hugo 内容
        filename = markdown_generator.generate_filename(title)
        full_content = markdown_generator.wrap_with_front_matter(
            title=title,
            content=content,
            date=date,
            tags=tags,
            category=category,
            draft=draft
        )
        
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
                'url': result['url']
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
