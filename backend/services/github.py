#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub上传服务
"""

import os
import base64
import time
import requests
from typing import Optional, Dict, Any


class GitHubService:
    """GitHub API服务类"""
    
    def __init__(self):
        self.token = os.environ.get('GITHUB_TOKEN', '')
        self.username = os.environ.get('GITHUB_USERNAME', '')
        self.repo = os.environ.get('GITHUB_REPO', '')
        
        if not self.token:
            raise ValueError('未设置GitHub Token，请配置环境变量GITHUB_TOKEN')
        if not self.username:
            raise ValueError('未设置GitHub用户名，请配置环境变量GITHUB_USERNAME')
        if not self.repo:
            raise ValueError('未设置GitHub仓库名，请配置环境变量GITHUB_REPO')
        
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
    
    def _get_file_sha(self, path: str, max_retries: int = 3) -> Optional[str]:
        """
        获取文件的SHA值（用于更新文件），带自动重试机制
        
        参数:
            path: 文件在仓库中的路径
            max_retries: 最大重试次数
            
        返回:
            文件的SHA值，如果文件不存在则返回None
        """
        url = f'{self.base_url}/repos/{self.username}/{self.repo}/contents/{path}'
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                
                if response.status_code == 200:
                    return response.json().get('sha')
                elif response.status_code == 404:
                    return None
                else:
                    response.raise_for_status()
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # 重试前等待，时间递增
                    wait_time = (attempt + 1) * 2  # 2秒, 4秒
                    print(f"获取文件SHA失败（第{attempt + 1}次尝试），{wait_time}秒后重试: {str(e)}")
                    time.sleep(wait_time)
                continue
        
        raise Exception(f'获取文件SHA失败（已重试{max_retries}次）：{str(last_exception)}')
    
    def upload_file(self, content: str, filename: str, target_dir: str = 'content/posts',
                   message: str = 'Update file', branch: str = 'main', is_binary: bool = False) -> Dict[str, Any]:
        """
        上传文件到GitHub仓库
        
        参数:
            content: 文件内容（文本或base64编码的二进制内容）
            filename: 文件名
            target_dir: 目标目录
            message: 提交信息
            branch: 分支名
            is_binary: 是否为二进制内容（如果是，则直接使用content，不再进行utf-8编码）
            
        返回:
            包含上传结果的字典
        """
        path = f'{target_dir}/{filename}'.lstrip('/')
        
        try:
            sha = self._get_file_sha(path)
            
            if is_binary:
                # 已经是 base64 字符串
                encoded_content = content
            else:
                # 文本内容，需要先编码再 base64
                encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            payload = {
                'message': message,
                'content': encoded_content,
                'branch': branch
            }
            
            if sha:
                payload['sha'] = sha
            
            url = f'{self.base_url}/repos/{self.username}/{self.repo}/contents/{path}'
            
            response = requests.put(url, headers=self.headers, json=payload, timeout=30)
            
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'success': True,
                'file_path': path,
                'url': result.get('content', {}).get('html_url', ''),
                'sha': result.get('content', {}).get('sha', '')
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_directory(self, path: str, message: str = 'Create directory') -> Dict[str, Any]:
        """
        在GitHub仓库中创建目录
        
        参数:
            path: 目录路径
            message: 提交信息
            
        返回:
            包含创建结果的字典
        """
        try:
            placeholder_content = base64.b64encode(b'').decode('utf-8')
            
            placeholder_path = f'{path}/.gitkeep'
            
            sha = self._get_file_sha(placeholder_path)
            
            payload = {
                'message': message,
                'content': placeholder_content,
                'branch': 'main'
            }
            
            if sha:
                payload['sha'] = sha
            
            url = f'{self.base_url}/repos/{self.username}/{self.repo}/contents/{placeholder_path}'
            
            response = requests.put(url, headers=self.headers, json=payload, timeout=30)
            
            response.raise_for_status()
            
            return {
                'success': True,
                'path': path
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_file(self, path: str, message: str = 'Delete file') -> Dict[str, Any]:
        """
        删除GitHub仓库中的文件
        
        参数:
            path: 文件路径
            message: 提交信息
            
        返回:
            包含删除结果的字典
        """
        try:
            sha = self._get_file_sha(path)
            
            if not sha:
                return {
                    'success': False,
                    'error': '文件不存在'
                }
            
            payload = {
                'message': message,
                'sha': sha,
                'branch': 'main'
            }
            
            url = f'{self.base_url}/repos/{self.username}/{self.repo}/contents/{path}'
            
            response = requests.delete(url, headers=self.headers, json=payload, timeout=30)
            
            response.raise_for_status()
            
            return {
                'success': True,
                'path': path
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_file_content(self, path: str) -> Dict[str, Any]:
        """
        获取GitHub仓库中文件的内容
        
        参数:
            path: 文件路径
            
        返回:
            包含文件内容的字典
        """
        try:
            url = f'{self.base_url}/repos/{self.username}/{self.repo}/contents/{path}'
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 404:
                return {
                    'success': False,
                    'error': '文件不存在'
                }
            
            response.raise_for_status()
            
            result = response.json()
            
            content = base64.b64decode(result.get('content', '')).decode('utf-8')
            
            return {
                'success': True,
                'content': content,
                'path': path,
                'sha': result.get('sha', '')
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_files(self, path: str = '', fetch_metadata: bool = False) -> Dict[str, Any]:
        """
        列出仓库目录中的文件
        
        参数:
            path: 目录路径
            fetch_metadata: 是否获取每个文件的元数据 (如 front matter 中的 date)
            
        返回:
            包含文件列表的字典
        """
        import re
        from concurrent.futures import ThreadPoolExecutor

        try:
            url = f'{self.base_url}/repos/{self.username}/{self.repo}/contents/{path}'
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            response.raise_for_status()
            
            files = response.json()
            
            if isinstance(files, dict):
                files = files.get('children', [])
            
            file_list = []
            
            def process_file(f):
                file_type = f.get('type', '')
                item = {
                    'name': f.get('name', ''),
                    'path': f.get('path', ''),
                    'type': file_type,
                    'is_dir': file_type == 'dir',
                    'size': f.get('size', 0),
                    'url': f.get('html_url', ''),
                    'updated_at': None # 默认占位
                }
                
                if fetch_metadata and item['type'] == 'file' and item['name'].endswith(('.md', '.markdown')):
                    try:
                        content_res = self.get_file_content(item['path'])
                        if content_res['success']:
                            content = content_res['content']
                            # 简单正则提取 date: "..."
                            date_match = re.search(r'^date:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
                            if date_match:
                                item['updated_at'] = date_match.group(1)
                    except Exception as e:
                        print(f"Error fetching metadata for {item['name']}: {e}")
                
                return item

            if fetch_metadata:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    file_list = list(executor.map(process_file, files))
            else:
                for f in files:
                    file_list.append(process_file(f))
            
            return {
                'success': True,
                'path': path,
                'files': file_list
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_repo_info(self, max_retries: int = 3) -> Dict[str, Any]:
        """
        获取仓库信息，带自动重试机制
        
        返回:
            包含仓库信息的字典
        """
        url = f'{self.base_url}/repos/{self.username}/{self.repo}'
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                
                response.raise_for_status()
                
                result = response.json()
                
                return {
                    'success': True,
                    'name': result.get('name', ''),
                    'full_name': result.get('full_name', ''),
                    'description': result.get('description', ''),
                    'default_branch': result.get('default_branch', 'main'),
                    'url': result.get('html_url', '')
                }
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"获取仓库信息失败（第{attempt + 1}次尝试），{wait_time}秒后重试: {str(e)}")
                    time.sleep(wait_time)
                continue
        
        return {
            'success': False,
            'error': f'获取仓库信息失败（已重试{max_retries}次）：{str(last_exception)}'
        }
    
    def validate_config(self) -> Dict[str, Any]:
        """
        验证GitHub配置是否正确
        
        返回:
            包含验证结果的字典
        """
        try:
            repo_info = self.get_repo_info()
            
            if not repo_info['success']:
                return {
                    'valid': False,
                    'error': repo_info.get('error', '获取仓库信息失败')
                }
            
            return {
                'valid': True,
                'message': 'GitHub配置正确',
                'repo': repo_info
            }
        
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    def get_latest_workflow_run(self) -> Dict[str, Any]:
        """
        获取最近的 GitHub Actions 运行状态，优先返回正在运行的任务
        
        返回:
            包含运行状态的字典
        """
        try:
            # 抓取最近 5 个任务，以便识别是否存在并发运行的情况
            url = f'{self.base_url}/repos/{self.username}/{self.repo}/actions/runs?per_page=5'
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            runs = data.get('workflow_runs', [])
            
            if not runs:
                return {
                    'success': True,
                    'result': None
                }
            
            # 优先寻找正在运行 (in_progress) 或排队中 (queued) 的任务
            active_run = next((r for r in runs if r.get('status') in ['in_progress', 'queued', 'pending']), None)
            
            # 如果有活跃任务，使用活跃任务；否则使用最近的一个任务
            target_run = active_run if active_run else runs[0]
            
            return {
                'success': True,
                'result': {
                    'status': target_run.get('status'),
                    'conclusion': target_run.get('conclusion'),
                    'html_url': target_run.get('html_url'),
                    'id': target_run.get('id'),
                    'total_count': data.get('total_count', 0),
                    'active_count': sum(1 for r in runs if r.get('status') in ['in_progress', 'queued', 'pending'])
                }
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
