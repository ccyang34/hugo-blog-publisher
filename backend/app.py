#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hugo博客发布器 - Flask后端API
"""

import os
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from .services.deepseek import DeepSeekService
from .services.github import GitHubService
from .utils.markdown import MarkdownGenerator

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
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/', methods=['GET'])
def index():
    """主页 - API 测试界面"""
    return render_template('index.html')


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
        
        formatted_content = deepseek_service.format_article(
            content=content,
            title=title,
            tags=tags,
            category=category
        )
        
        return jsonify({
            'success': True,
            'formatted_content': formatted_content
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
        date = data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M'))
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
        date = data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M'))
        tags = data.get('tags', [])
        category = data.get('category', '')
        target_dir = data.get('target_dir', 'content/posts')
        draft = data.get('draft', False)
        auto_format = data.get('auto_format', True)  # 默认自动优化排版
        
        # 自动调用 DeepSeek 优化排版
        if auto_format:
            try:
                content = deepseek_service.format_article(
                    content=content,
                    title=title,
                    tags=tags,
                    category=category
                )
            except Exception as e:
                # 优化失败时继续使用原内容
                print(f"Warning: Auto format failed: {e}")
        
        # 如果没有标题，调用 DeepSeek 自动生成
        if not title:
            try:
                title = deepseek_service.improve_title(content)
            except Exception as e:
                # 生成失败时使用默认标题
                title = f"未命名文章_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
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
        result = github_service.list_files(path)
        
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
