class HugoPublisher {
    constructor() {
        this.apiBaseUrl = window.APP_CONFIG?.apiBaseUrl || '';
        this.currentContent = '';
        this.frontMatter = {};
        this.uploadedImages = [];
        
        this.initElements();
        this.bindEvents();
        this.checkApiHealth();
    }
    
    initElements() {
        this.titleInput = document.getElementById('title');
        this.categorySelect = document.getElementById('category');
        this.tagsInput = document.getElementById('tags');
        this.contentTextarea = document.getElementById('content');
        
        this.formatBtn = document.getElementById('formatBtn');
        this.previewBtn = document.getElementById('previewBtn');
        this.publishBtn = document.getElementById('publishBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.sampleBtn = document.getElementById('sampleBtn');
        
        this.previewContent = document.getElementById('previewContent');
        this.markdownContent = document.getElementById('markdownContent');
        this.frontMatterContent = document.getElementById('frontMatterContent');
        
        this.wordCountEl = document.getElementById('wordCount');
        this.readingTimeEl = document.getElementById('readingTime');
        
        this.targetDirSelect = document.getElementById('targetDir');
        this.isDraftCheckbox = document.getElementById('isDraft');
        
        this.publishResult = document.getElementById('publishResult');
        this.successMessage = document.getElementById('successMessage');
        this.viewLink = document.getElementById('viewLink');
        this.errorMessage = document.getElementById('errorMessage');
        
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.loadingText = document.getElementById('loadingText');
        
        this.tabs = document.querySelectorAll('.tab');
        this.tabContents = document.querySelectorAll('.tab-content');
        
        this.imageInput = document.getElementById('imageInput');
        this.imageList = document.getElementById('imageList');
        this.imageUploadProgress = document.getElementById('imageUploadProgress');
        this.progressFill = this.imageUploadProgress.querySelector('.progress-fill');
        this.progressText = this.imageUploadProgress.querySelector('.progress-text');
    }
    
    bindEvents() {
        this.formatBtn.addEventListener('click', () => this.formatArticle());
        this.previewBtn.addEventListener('click', () => this.previewArticle());
        this.publishBtn.addEventListener('click', () => this.publishArticle());
        this.clearBtn.addEventListener('click', () => this.clearForm());
        this.sampleBtn.addEventListener('click', () => this.loadSample());
        
        this.contentTextarea.addEventListener('input', () => this.updateStats());
        this.contentTextarea.addEventListener('paste', (e) => this.handlePaste(e));
        
        this.tabs.forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });
        
        this.imageInput.addEventListener('change', (e) => this.handleImageSelect(e));
    }
    
    async checkApiHealth() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/health`);
            if (!response.ok) {
                this.showNotification('后端服务不可用，请检查配置', 'error');
            }
        } catch (error) {
            console.warn('API健康检查失败:', error);
        }
    }
    
    showLoading(message = '处理中...') {
        this.loadingText.textContent = message;
        this.loadingOverlay.classList.remove('hidden');
    }
    
    hideLoading() {
        this.loadingOverlay.classList.add('hidden');
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 1001;
            animation: slideIn 0.3s ease;
            background: ${type === 'error' ? '#dc2626' : type === 'success' ? '#16a34a' : '#2563eb'};
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    async formatArticle() {
        const content = this.contentTextarea.value.trim();
        
        if (!content) {
            this.showNotification('请输入文章内容', 'error');
            return;
        }
        
        this.setButtonsDisabled(true);
        this.showLoading('正在使用DeepSeek优化文章排版...');
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/format`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    title: this.titleInput.value.trim(),
                    tags: this.getTags(),
                    category: this.categorySelect.value
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentContent = data.formatted_content;
                this.updatePreview(data.formatted_content);
                this.markdownContent.value = data.formatted_content;
                this.showNotification('文章排版完成!', 'success');
            } else {
                this.showNotification(`排版失败: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('格式化错误:', error);
            this.showNotification(`网络错误: ${error.message}`, 'error');
        } finally {
            this.setButtonsDisabled(false);
            this.hideLoading();
        }
    }
    
    async previewArticle() {
        const title = this.titleInput.value.trim();
        const content = this.currentContent || this.contentTextarea.value.trim();
        
        if (!title) {
            this.showNotification('请输入文章标题', 'error');
            return;
        }
        
        if (!content) {
            this.showNotification('请输入文章内容', 'error');
            return;
        }
        
        this.showLoading('正在生成预览...');
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/preview`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: title,
                    content: content,
                    tags: this.getTags(),
                    category: this.categorySelect.value
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.frontMatter = data.front_matter;
                this.frontMatterContent.value = data.front_matter;
                this.updateStats();
                this.showNotification('预览生成完成!', 'success');
            } else {
                this.showNotification(`预览生成失败: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('预览错误:', error);
            this.showNotification(`网络错误: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    async publishArticle() {
        const title = this.titleInput.value.trim();
        const content = this.currentContent || this.contentTextarea.value.trim();
        
        if (!title) {
            this.showNotification('请输入文章标题', 'error');
            return;
        }
        
        if (!content) {
            this.showNotification('请输入文章内容', 'error');
            return;
        }
        
        this.publishBtn.disabled = true;
        this.showLoading('正在发布到GitHub...');
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/publish`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: title,
                    content: content,
                    tags: this.getTags(),
                    category: this.categorySelect.value,
                    target_dir: this.targetDirSelect.value,
                    draft: this.isDraftCheckbox.checked
                })
            });
            
            const data = await response.json();
            
            this.publishResult.classList.remove('hidden');
            
            if (data.success) {
                this.publishResult.querySelector('.result-success').classList.remove('hidden');
                this.publishResult.querySelector('.result-error').classList.add('hidden');
                this.successMessage.textContent = `文章已成功发布到 ${data.file_path}`;
                this.viewLink.href = data.url;
                this.showNotification('发布成功!', 'success');
            } else {
                this.publishResult.querySelector('.result-success').classList.add('hidden');
                this.publishResult.querySelector('.result-error').classList.remove('hidden');
                this.errorMessage.textContent = data.error || '发布失败，请稍后重试';
                this.showNotification(`发布失败: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('发布错误:', error);
            this.publishResult.classList.remove('hidden');
            this.publishResult.querySelector('.result-success').classList.add('hidden');
            this.publishResult.querySelector('.result-error').classList.remove('hidden');
            this.errorMessage.textContent = `网络错误: ${error.message}`;
            this.showNotification(`发布失败: ${error.message}`, 'error');
        } finally {
            this.publishBtn.disabled = false;
            this.hideLoading();
        }
    }
    
    updatePreview(markdown) {
        const html = this.markdownToHtml(markdown);
        this.previewContent.innerHTML = html;
    }
    
    markdownToHtml(markdown) {
        let html = markdown
            .replace(/^### (.+)$/gm, '<h3>$1</h3>')
            .replace(/^## (.+)$/gm, '<h2>$1</h2>')
            .replace(/^# (.+)$/gm, '<h1>$1</h1>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`(.+?)`/g, '<code>$1</code>')
            .replace(/```(\w+)?\n([\s\S]+?)```/g, '<pre><code class="language-$1">$2</code></pre>')
            .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>')
            .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
            .replace(/^- (.+)$/gm, '<li>$1</li>')
            .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/^(?!<)(.+)$/gm, '<p>$1</p>');
        
        html = html.replace(/<li>.*<\/li>/s, (match) => {
            if (match.includes('<ul>') || match.includes('<ol>')) {
                return match;
            }
            return '<ul>' + match + '</ul>';
        });
        
        return html;
    }
    
    updateStats() {
        const content = this.currentContent || this.contentTextarea.value;
        const words = content.replace(/\s/g, '').length;
        const readingTime = Math.ceil(words / 200);
        
        this.wordCountEl.textContent = `${words} 字`;
        this.readingTimeEl.textContent = `约 ${readingTime} 分钟`;
    }
    
    switchTab(tabId) {
        this.tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabId);
        });
        
        this.tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `${tabId}Tab`);
        });
    }
    
    getTags() {
        const tagsValue = this.tagsInput.value.trim();
        if (!tagsValue) return [];
        return tagsValue.split(',').map(tag => tag.trim()).filter(tag => tag);
    }
    
    clearForm() {
        this.titleInput.value = '';
        this.categorySelect.value = '';
        this.tagsInput.value = '';
        this.contentTextarea.value = '';
        this.currentContent = '';
        this.frontMatter = {};
        this.previewContent.innerHTML = '<p class="placeholder-text">格式化后的文章预览将显示在这里...</p>';
        this.markdownContent.value = '';
        this.frontMatterContent.value = '';
        this.updateStats();
        this.publishResult.classList.add('hidden');
        this.showNotification('已清空表单', 'info');
    }
    
    loadSample() {
        this.titleInput.value = '使用DeepSeek优化博客文章排版';
        this.categorySelect.value = '技术';
        this.tagsInput.value = 'Hugo, DeepSeek, AI, 博客';
        this.contentTextarea.value = `在当今快节奏的数字时代，博客文章的排版和内容质量直接影响读者的阅读体验和搜索引擎优化效果。本文将介绍如何使用DeepSeek AI来优化博客文章的排版，让你的内容更加专业、易读。

为什么文章排版很重要

良好的文章排版能够：
1. 提高可读性，让读者更容易理解内容
2. 增强视觉吸引力，降低跳出率
3. 改善SEO效果，提高搜索排名
4. 塑造专业形象，增加读者信任

使用DeepSeek进行文章优化

DeepSeek是一个强大的AI工具，可以帮助我们：
- 优化段落结构
- 修正语法错误
- 添加适当的小标题
- 改进句子表达
- 生成合适的标签

总结

通过使用AI工具优化文章排版，我们可以显著提高内容质量和读者体验。希望这篇文章对你有所帮助！

如果你有任何问题或建议，欢迎在评论区留言讨论。`;

        this.updateStats();
        this.showNotification('已加载示例文章', 'info');
    }
    
    async handlePaste(e) {
        const items = e.clipboardData?.items;
        if (!items) return;
        
        for (const item of items) {
            if (item.type.startsWith('image/')) {
                e.preventDefault();
                const file = item.getAsFile();
                await this.uploadImage(file);
                break;
            }
        }
    }
    
    async handleImageSelect(e) {
        const file = e.target.files[0];
        if (file) {
            await this.uploadImage(file);
        }
        e.target.value = '';
    }
    
    async uploadImage(file) {
        const maxSize = 10 * 1024 * 1024;
        if (file.size > maxSize) {
            this.showNotification('图片大小不能超过10MB', 'error');
            return;
        }
        
        this.imageUploadProgress.classList.remove('hidden');
        this.progressFill.style.width = '0%';
        this.progressText.textContent = '上传中...';
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch(`${this.apiBaseUrl}/api/upload-image`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.progressFill.style.width = '100%';
                this.progressText.textContent = '上传成功!';
                
                this.uploadedImages.push({
                    url: data.url,
                    filename: data.filename,
                    timestamp: Date.now()
                });
                
                this.renderUploadedImages();
                this.insertImageToContent(data.url, file.name);
                this.showNotification('图片上传成功!', 'success');
            } else {
                this.progressText.textContent = '上传失败';
                this.showNotification(`上传失败: ${data.error}`, 'error');
            }
        } catch (error) {
            this.progressText.textContent = '上传失败';
            this.showNotification(`网络错误: ${error.message}`, 'error');
        } finally {
            setTimeout(() => {
                this.imageUploadProgress.classList.add('hidden');
            }, 1500);
        }
    }
    
    insertImageToContent(url, filename) {
        const imageMarkdown = `![${filename}](${url})`;
        const textarea = this.contentTextarea;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const text = textarea.value;
        
        const newText = text.substring(0, start) + imageMarkdown + text.substring(end);
        textarea.value = newText;
        
        const newCursorPos = start + imageMarkdown.length;
        textarea.selectionStart = textarea.selectionEnd = newCursorPos;
        textarea.focus();
        
        this.updateStats();
    }
    
    renderUploadedImages() {
        this.imageList.innerHTML = '';
        
        this.uploadedImages.forEach((img, index) => {
            const item = document.createElement('div');
            item.className = 'uploaded-image-item';
            item.innerHTML = `
                <img src="${img.url}" alt="${img.filename}" title="${img.filename}">
                <button class="copy-btn" title="复制链接">📋</button>
                <button class="delete-btn" title="删除">×</button>
            `;
            
            item.querySelector('.copy-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                navigator.clipboard.writeText(`![${img.filename}](${img.url})`);
                this.showNotification('已复制图片链接!', 'success');
            });
            
            item.querySelector('.delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.uploadedImages.splice(index, 1);
                this.renderUploadedImages();
                this.removeImageFromContent(img.url);
            });
            
            this.imageList.appendChild(item);
        });
    }
    
    removeImageFromContent(url) {
        const textarea = this.contentTextarea;
        const regex = new RegExp(`!\\[.*?\\]\\(${url}\\)`, 'g');
        textarea.value = textarea.value.replace(regex, '');
        this.updateStats();
    }
    
    setButtonsDisabled(disabled) {
        this.formatBtn.disabled = disabled;
        this.previewBtn.disabled = disabled;
        this.publishBtn.disabled = disabled;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new HugoPublisher();
});
