class HugoPublisher {
    constructor() {
        this.apiBaseUrl = window.APP_CONFIG?.apiBaseUrl || '';
        this.currentContent = '';
        this.frontMatter = {};
        this.uploadedImages = [];
        this.jobs = []; // Store active jobs

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

        this.publishBtn = document.getElementById('publishBtn');
        this.publishBtnLeft = document.getElementById('publishBtnLeft');
        this.clearBtn = document.getElementById('clearBtn');
        this.sampleBtn = document.getElementById('sampleBtn');
        this.toggleMetadataBtn = document.getElementById('toggleMetadataBtn');
        this.metadataSection = document.getElementById('metadataSection');

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

        this.fileList = document.getElementById('fileList');
        this.fileDirSelect = document.getElementById('fileDirSelect');
        this.refreshFilesBtn = document.getElementById('refreshFilesBtn');

        // Job Queue Elements
        this.jobQueueModal = document.getElementById('jobQueueModal');
        this.jobList = document.getElementById('jobList');
        if (this.jobQueueModal) {
            this.jobQueueModal.querySelector('.modal-close').addEventListener('click', () => {
                this.jobQueueModal.classList.add('hidden');
            });
        }
    }

    bindEvents() {
        this.formatBtn.addEventListener('click', () => this.formatArticle());

        this.publishBtn.addEventListener('click', () => this.handlePublishWithPassword());
        if (this.publishBtnLeft) {
            this.publishBtnLeft.addEventListener('click', () => this.handlePublishWithPassword());
        }
        this.clearBtn.addEventListener('click', () => this.clearForm());
        this.sampleBtn.addEventListener('click', () => this.loadSample());

        if (this.toggleMetadataBtn) {
            this.toggleMetadataBtn.addEventListener('click', () => {
                this.metadataSection.classList.toggle('hidden');
            });
        }

        this.contentTextarea.addEventListener('input', () => this.updateStats());
        this.contentTextarea.addEventListener('paste', (e) => this.handlePaste(e));

        this.tabs.forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        this.refreshFilesBtn.addEventListener('click', () => this.loadFiles());
        this.fileDirSelect.addEventListener('change', () => this.loadFiles());

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

                // 自动填充生成的建议信息
                if (!this.titleInput.value.trim() && data.suggested_title) {
                    this.titleInput.value = data.suggested_title;
                }
                if (data.suggested_category) {
                    this.categorySelect.value = data.suggested_category;
                }
                if (data.suggested_tags && data.suggested_tags.length > 0) {
                    this.tagsInput.value = data.suggested_tags.join(', ');
                }

                this.showNotification('文章分析及预览完成!', 'success');
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



    async handlePublishWithPassword() {
        const title = this.titleInput.value.trim();
        const content = this.currentContent || this.contentTextarea.value.trim();

        if (!content) {
            this.showNotification('请输入文章内容', 'error');
            return;
        }

        // Check for multiple URLs
        const lines = content.split('\n').map(line => line.trim()).filter(line => line);
        const urlPattern = /^https?:\/\/\S+$/;

        // If all non-empty lines are URLs and there are more than 1
        const isBatchUrl = lines.length > 1 && lines.every(line => urlPattern.test(line));

        if (sessionStorage.getItem('hugo_authenticated') === 'true') {
            if (isBatchUrl) {
                this.publishBatch(lines);
            } else {
                this.publishArticle();
            }
        } else {
            this.showPasswordDialog('发布文章', () => {
                if (isBatchUrl) {
                    this.publishBatch(lines);
                } else {
                    this.publishArticle();
                }
            });
        }
    }

    async publishBatch(urls) {
        this.jobs = []; // Reset jobs
        this.jobQueueModal.classList.remove('hidden');
        this.jobList.innerHTML = '';

        this.showNotification(`开始批量处理 ${urls.length} 个任务...`, 'success');

        // Initialize jobs in UI
        urls.forEach((url, index) => {
            this.jobs.push({
                id: null, // Will be set after submission
                tempId: index,
                title: url, // Show URL as title initially
                status: 'pending',
                progress: 0,
                message: '等待提交...',
                url: url
            });
        });
        this.renderJobQueue();

        // Submit all jobs sequentially to backend (or parallel, but backend is queue-based anyway)
        for (let i = 0; i < urls.length; i++) {
            const url = urls[i];
            try {
                // Submit job
                const response = await fetch(`${this.apiBaseUrl}/api/publish`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title: '', // Auto-detect
                        content: url,
                        tags: this.getTags(),
                        category: this.categorySelect.value,
                        target_dir: this.targetDirSelect.value,
                        draft: this.isDraftCheckbox.checked,
                        auto_format: true
                    })
                });

                const data = await response.json();
                if (data.success) {
                    this.jobs[i].id = data.job_id;
                    this.jobs[i].status = 'queued';
                    this.jobs[i].message = '已加入队列';
                    this.jobs[i].progress = 10;
                } else {
                    this.jobs[i].status = 'failed';
                    this.jobs[i].message = data.error || '提交失败';
                }
            } catch (error) {
                this.jobs[i].status = 'failed';
                this.jobs[i].message = `网络错误: ${error.message}`;
            }
            this.renderJobQueue();
        }

        // Start polling
        this.pollJobs();
    }

    async publishArticle() {
        const title = this.titleInput.value.trim();
        // 判断是否已手动优化过
        const alreadyFormatted = !!this.currentContent;
        const content = this.currentContent || this.contentTextarea.value.trim();

        // 标题可选，由 DeepSeek 自动生成
        if (!content) {
            this.showNotification('请输入文章内容', 'error');
            return;
        }

        this.publishBtn.disabled = true;
        if (this.publishBtnLeft) this.publishBtnLeft.disabled = true;

        // Use Job Queue UI for single tasks too, for consistency? 
        // Or stick to simple loading overlay for single tasks? 
        // Let's use Job Queue UI if it's cleaner, but maybe stick to overlay for single tasks to minimize change impact unless requested.
        // Actually, let's use the new queue system for everything to be consistent.

        this.jobs = [{
            id: null,
            tempId: 0,
            title: title || '新文章',
            status: 'pending',
            progress: 0,
            message: '正在提交...'
        }];

        // Show Queue Modal instead of Loading Overlay
        this.jobQueueModal.classList.remove('hidden');
        this.renderJobQueue();

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
                    draft: this.isDraftCheckbox.checked,
                    auto_format: !alreadyFormatted  // 已手动优化则跳过自动优化
                })
            });

            const data = await response.json();

            if (data.success && data.job_id) {
                this.jobs[0].id = data.job_id;
                this.jobs[0].status = 'queued';
                this.jobs[0].message = '已加入队列';
                this.renderJobQueue();
                this.pollJobs();
            } else {
                this.jobs[0].status = 'failed';
                this.jobs[0].message = data.error || '发布失败';
                this.renderJobQueue();
                this.handlePublishError(data.error || '发布失败');
            }
        } catch (error) {
            console.error('发布错误:', error);
            this.jobs[0].status = 'failed';
            this.jobs[0].message = `网络错误: ${error.message}`;
            this.renderJobQueue();
            this.handlePublishError(`网络错误: ${error.message}`);
        }
    }

    renderJobQueue() {
        this.jobList.innerHTML = '';
        this.jobs.forEach(job => {
            const item = document.createElement('div');
            item.className = 'job-item';

            const statusClass = `status-${job.status}`;
            const statusText = {
                'pending': '等待中',
                'queued': '排队中',
                'processing': '处理中',
                'completed': '完成',
                'failed': '失败'
            }[job.status] || job.status;

            let resultLink = '';
            if (job.status === 'completed' && job.result) {
                resultLink = `<a href="${job.result.url}" target="_blank" class="job-link">查看文章</a>`;
            }

            item.innerHTML = `
                <div class="job-header">
                    <span class="job-title" title="${job.title}">${job.title || '处理中...'}</span>
                    <span class="job-status ${statusClass}">${statusText}</span>
                </div>
                <div class="job-progress-bar">
                    <div class="job-progress-fill" style="width: ${job.progress}%"></div>
                </div>
                <div class="job-header" style="margin-bottom: 0;">
                    <span class="job-message">${job.message}</span>
                    ${resultLink}
                </div>
            `;
            this.jobList.appendChild(item);
        });
    }

    async pollJobs() {
        const pollInterval = 1000;
        let activeJobs = this.jobs.filter(j => j.id && !['completed', 'failed'].includes(j.status));

        if (activeJobs.length === 0) {
            // All done (or none started)
            this.setButtonsDisabled(false);

            // If all completed successfully
            if (this.jobs.every(j => j.status === 'completed')) {
                this.showNotification('所有任务处理完成!', 'success');
            }
            return;
        }

        // Poll each active job
        for (const job of activeJobs) {
            try {
                const response = await fetch(`${this.apiBaseUrl}/api/status/${job.id}`);
                const data = await response.json();

                if (data.success) {
                    const updatedJob = data.job;
                    // Update local job state
                    job.status = updatedJob.status;
                    job.progress = updatedJob.progress;
                    job.message = updatedJob.message;
                    job.result = updatedJob.result;
                    if (updatedJob.error) job.error = updatedJob.error;

                    // If we found a refined title, update it
                    // (Backend doesn't return title in status, but maybe we can infer or backend could added it. 
                    //  For now, use message or just keep URL)
                }
            } catch (error) {
                console.error(`Poll error for ${job.id}:`, error);
            }
        }

        this.renderJobQueue();

        // Continue polling if there are still active jobs
        setTimeout(() => this.pollJobs(), pollInterval);
    }

    showPasswordDialog(action, onSuccess) {
        // 移除已存在的对话框
        const existingDialog = document.getElementById('passwordDialog');
        if (existingDialog) existingDialog.remove();

        const dialog = document.createElement('div');
        dialog.id = 'passwordDialog';
        dialog.className = 'modal';
        dialog.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>🔐 密码验证</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <p>请输入密码以${action}：</p>
                    <input type="password" id="passwordInput" class="form-input" placeholder="请输入密码" autocomplete="off">
                    <p id="passwordError" class="error-text" style="display: none;"></p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" id="cancelPasswordBtn">取消</button>
                    <button class="btn btn-primary" id="confirmPasswordBtn">确认</button>
                </div>
            </div>
        `;
        document.body.appendChild(dialog);

        const passwordInput = dialog.querySelector('#passwordInput');
        const passwordError = dialog.querySelector('#passwordError');
        const confirmBtn = dialog.querySelector('#confirmPasswordBtn');
        const cancelBtn = dialog.querySelector('#cancelPasswordBtn');
        const closeBtn = dialog.querySelector('.modal-close');

        passwordInput.focus();

        const closeDialog = () => dialog.remove();

        const handleConfirm = async () => {
            const password = passwordInput.value;
            if (!password) {
                passwordError.textContent = '请输入密码';
                passwordError.style.display = 'block';
                return;
            }

            confirmBtn.disabled = true;
            confirmBtn.textContent = '验证中...';

            const isValid = await this.verifyPassword(password);
            if (isValid) {
                closeDialog();
                onSuccess();
            } else {
                passwordError.textContent = '密码错误，请重试';
                passwordError.style.display = 'block';
                confirmBtn.disabled = false;
                confirmBtn.textContent = '确认';
                passwordInput.value = '';
                passwordInput.focus();
            }
        };

        confirmBtn.addEventListener('click', handleConfirm);
        cancelBtn.addEventListener('click', closeDialog);
        closeBtn.addEventListener('click', closeDialog);
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog) closeDialog();
        });
        passwordInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') handleConfirm();
            if (e.key === 'Escape') closeDialog();
        });
    }

    async verifyPassword(password) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/verify-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });
            const data = await response.json();
            if (data.success === true) {
                sessionStorage.setItem('hugo_authenticated', 'true');
                return true;
            }
            return false;
        } catch (error) {
            console.error('密码验证错误:', error);
            return false;
        }
    }

    async publishArticle() {
        const title = this.titleInput.value.trim();
        // 判断是否已手动优化过
        const alreadyFormatted = !!this.currentContent;
        const content = this.currentContent || this.contentTextarea.value.trim();

        // 标题可选，由 DeepSeek 自动生成
        if (!content) {
            this.showNotification('请输入文章内容', 'error');
            return;
        }

        this.publishBtn.disabled = true;
        if (this.publishBtnLeft) this.publishBtnLeft.disabled = true;
        // 根据是否需要自动优化显示不同提示
        const loadingMsg = alreadyFormatted ? '正在提交发布任务...' : '正在提交AI优化任务...';
        this.showLoading(loadingMsg);

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
                    draft: this.isDraftCheckbox.checked,
                    auto_format: !alreadyFormatted  // 已手动优化则跳过自动优化
                })
            });

            const data = await response.json();

            if (data.success && data.job_id) {
                this.showNotification('任务提交成功，正在后台处理...', 'success');
                this.pollStatus(data.job_id);
            } else {
                this.handlePublishError(data.error || '发布失败');
            }
        } catch (error) {
            console.error('发布错误:', error);
            this.handlePublishError(`网络错误: ${error.message}`);
        }
    }

    async pollStatus(jobId) {
        const pollInterval = 1000; // 1 second

        const checkStatus = async () => {
            try {
                const response = await fetch(`${this.apiBaseUrl}/api/status/${jobId}`);
                const data = await response.json();

                if (data.success) {
                    const job = data.job;
                    this.showLoading(`${job.message} (${job.progress}%)`);

                    if (job.status === 'completed') {
                        this.handlePublishSuccess(job.result);
                    } else if (job.status === 'failed') {
                        this.handlePublishError(job.error);
                    } else {
                        // Continue polling
                        setTimeout(checkStatus, pollInterval);
                    }
                } else {
                    this.handlePublishError('无法获取任务状态');
                }
            } catch (error) {
                console.error('Polling error:', error);
                this.handlePublishError(`状态查询失败: ${error.message}`);
            }
        };

        // Start polling
        checkStatus();
    }

    handlePublishSuccess(result) {
        this.hideLoading();
        this.publishBtn.disabled = false;
        if (this.publishBtnLeft) this.publishBtnLeft.disabled = false;

        this.publishResult.classList.remove('hidden');
        this.publishResult.querySelector('.result-success').classList.remove('hidden');
        this.publishResult.querySelector('.result-error').classList.add('hidden');

        this.successMessage.textContent = `文章已成功发布到 ${result.file_path}`;
        this.viewLink.href = result.url;
        this.showNotification('发布成功!', 'success');
    }

    handlePublishError(errorMsg) {
        this.hideLoading();
        this.publishBtn.disabled = false;
        if (this.publishBtnLeft) this.publishBtnLeft.disabled = false;

        this.publishResult.classList.remove('hidden');
        this.publishResult.querySelector('.result-success').classList.add('hidden');
        this.publishResult.querySelector('.result-error').classList.remove('hidden');

        this.errorMessage.textContent = errorMsg;
        this.showNotification(`发布失败: ${errorMsg}`, 'error');
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
        this.publishBtn.disabled = disabled;
        if (this.publishBtnLeft) {
            this.publishBtnLeft.disabled = disabled;
        }
    }

    async loadFiles() {
        const path = this.fileDirSelect.value;
        this.fileList.innerHTML = '<p class="loading-text">加载中...</p>';

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/files?path=${encodeURIComponent(path)}&fetch_metadata=true`);
            const data = await response.json();

            if (data.success) {
                this.renderFiles(data.files);
            } else {
                this.fileList.innerHTML = `<p class="error-text">加载失败: ${data.error}</p>`;
            }
        } catch (error) {
            console.error('加载文件列表错误:', error);
            this.fileList.innerHTML = `<p class="error-text">网络错误: ${error.message}</p>`;
        }
    }

    renderFiles(files) {
        this.fileList.innerHTML = '';

        if (!files || files.length === 0) {
            this.fileList.innerHTML = '<p class="empty-text">该目录下没有文章</p>';
            return;
        }

        // 优先使用属性日期 (updated_at) 排序，否则回退到文件名
        const sortedFiles = [...files].sort((a, b) => {
            const dateA = a.updated_at ? new Date(a.updated_at) : new Date(0);
            const dateB = b.updated_at ? new Date(b.updated_at) : new Date(0);

            if (dateA.getTime() !== dateB.getTime()) {
                return dateB.getTime() - dateA.getTime();
            }
            return b.name.localeCompare(a.name, undefined, { numeric: true });
        });

        const dirMap = {
            'content/posts': '文章',
            'content/notes': '笔记',
            'content/drafts': '草稿'
        };
        const currentDir = this.fileDirSelect.value;
        const dirName = dirMap[currentDir] || '文件';

        sortedFiles.forEach(file => {
            const item = document.createElement('div');
            item.className = 'article-list-item';
            // item.style.cursor = 'pointer'; // 样式表中已定义

            let dateStr = '';
            if (file.updated_at) {
                const date = new Date(file.updated_at);
                dateStr = date.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                });
            }

            const displayName = file.name.replace(/\.md$/i, '');

            item.innerHTML = `
                <div class="item-content">
                    <div class="item-title" title="${file.name}">${displayName}</div>
                    <div class="item-meta">
                        <span class="item-dir">${dirName}</span>
                        <span class="item-date">${dateStr || '-'}</span>
                    </div>
                </div>
            `;

            // 绑定点击内容区域加载文章
            item.querySelector('.item-content').addEventListener('click', () => {
                this.loadFileContent(file.path);
            });

            this.fileList.appendChild(item);
        });
    }

    async loadFileContent(path) {
        this.showLoading('加载文章内容...');

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/file?path=${encodeURIComponent(path)}`);
            const data = await response.json();

            if (data.success) {
                // API 已返回解码后的 UTF-8 文本，直接使用
                const content = data.content;
                const lines = content.split('\n');
                let frontMatterEnd = 0;
                let markdownStart = 0;

                for (let i = 0; i < lines.length; i++) {
                    if (lines[i].trim() === '---') {
                        if (frontMatterEnd === 0) {
                            frontMatterEnd = i;
                        } else {
                            markdownStart = i + 1;
                            break;
                        }
                    }
                }

                const frontMatter = lines.slice(0, frontMatterEnd + 1).join('\n');
                const markdown = lines.slice(markdownStart).join('\n');

                this.frontMatterContent.value = frontMatter;
                this.markdownContent.value = markdown;
                this.contentTextarea.value = markdown;

                const frontMatterObj = this.parseFrontMatter(frontMatter);
                this.frontMatter = frontMatterObj;

                if (frontMatterObj.title) {
                    this.titleInput.value = frontMatterObj.title;
                }
                if (frontMatterObj.categories && frontMatterObj.categories.length > 0) {
                    this.categorySelect.value = frontMatterObj.categories[0];
                }
                if (frontMatterObj.tags && frontMatterObj.tags.length > 0) {
                    this.tagsInput.value = frontMatterObj.tags.join(', ');
                }

                this.updatePreview(markdown);
                this.updateStats();
                this.showNotification('文章加载成功!', 'success');
            } else {
                this.showNotification(`加载失败: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('加载文章错误:', error);
            this.showNotification(`网络错误: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    parseFrontMatter(frontMatter) {
        const result = {
            title: '',
            date: '',
            categories: [],
            tags: []
        };

        const lines = frontMatter.split('\n');
        let inFrontMatter = false;

        for (const line of lines) {
            const trimmed = line.trim();

            if (trimmed === '---') {
                if (!inFrontMatter) {
                    inFrontMatter = true;
                    continue;
                } else {
                    break;
                }
            }

            if (!inFrontMatter) continue;

            const colonIndex = trimmed.indexOf(':');
            if (colonIndex === -1) continue;

            const key = trimmed.slice(0, colonIndex).trim();
            const value = trimmed.slice(colonIndex + 1).trim();

            if (key === 'title') {
                result.title = value.replace(/^["']|["']$/g, '');
            } else if (key === 'date') {
                result.date = value;
            } else if (key === 'categories') {
                const match = value.match(/\[(.*)\]/);
                if (match) {
                    result.categories = match[1].split(',').map(c => c.trim().replace(/["']/g, ''));
                }
            } else if (key === 'tags') {
                const match = value.match(/\[(.*)\]/);
                if (match) {
                    result.tags = match[1].split(',').map(t => t.trim().replace(/["']/g, ''));
                }
            }
        }

        return result;
    }

    confirmDeleteFile(path, filename) {
        if (confirm(`确定要删除文章 "${filename}" 吗？\n\n此操作不可撤销！`)) {
            if (sessionStorage.getItem('hugo_authenticated') === 'true') {
                this.deleteFile(path, filename);
            } else {
                this.showPasswordDialog('删除文章', () => this.deleteFile(path, filename));
            }
        }
    }

    async deleteFile(path, filename) {
        this.showLoading('正在删除文章...');

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/file?path=${encodeURIComponent(path)}`, {
                method: 'DELETE'
            });
            const data = await response.json();

            if (data.success) {
                this.showNotification('文章删除成功!', 'success');
                this.loadFiles();
            } else {
                this.showNotification(`删除失败: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('删除文章错误:', error);
            this.showNotification(`网络错误: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new HugoPublisher();
});
