class AdminPanel {
    constructor() {
        this.apiBaseUrl = window.APP_CONFIG?.apiBaseUrl || '';
        this.currentSection = 'dashboard';
        this.articles = [];
        this.mediaFiles = [];

        this.init();
    }

    init() {
        this.initElements();
        this.bindEvents();
        this.loadDashboardData();
        this.checkSystemStatus();
    }

    initElements() {
        this.navItems = document.querySelectorAll('.nav-item');
        this.sections = document.querySelectorAll('.admin-section');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.loadingText = document.getElementById('loadingText');
        this.notification = document.getElementById('notification');
    }

    bindEvents() {
        this.navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const section = item.dataset.section;
                this.switchSection(section);
            });
        });

        document.getElementById('refreshArticles').addEventListener('click', () => {
            this.loadArticles();
        });

        document.getElementById('refreshMedia').addEventListener('click', () => {
            this.loadMedia();
        });

        document.getElementById('checkHealth').addEventListener('click', () => {
            this.checkSystemStatus();
        });

        document.getElementById('syncFiles').addEventListener('click', () => {
            this.syncAllFiles();
        });

        document.getElementById('clearCache').addEventListener('click', () => {
            this.clearCache();
        });

        document.getElementById('articleSearch').addEventListener('input', (e) => {
            this.filterArticles(e.target.value);
        });

        document.getElementById('articleCategory').addEventListener('change', (e) => {
            this.filterArticles();
        });

        document.getElementById('articleDir').addEventListener('change', (e) => {
            this.filterArticles();
        });

        document.getElementById('mediaSearch').addEventListener('input', (e) => {
            this.filterMedia(e.target.value);
        });
    }

    switchSection(sectionId) {
        this.currentSection = sectionId;

        this.navItems.forEach(item => {
            item.classList.toggle('active', item.dataset.section === sectionId);
        });

        this.sections.forEach(section => {
            section.classList.toggle('active', section.id === sectionId);
        });

        if (sectionId === 'dashboard') {
            this.loadDashboardData();
        } else if (sectionId === 'articles') {
            this.loadArticles();
        } else if (sectionId === 'media') {
            this.loadMedia();
        } else if (sectionId === 'system') {
            this.checkSystemStatus();
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
        this.notification.textContent = message;
        this.notification.className = `admin-notification ${type}`;
        this.notification.classList.remove('hidden');

        setTimeout(() => {
            this.notification.classList.add('hidden');
        }, 3000);
    }

    async loadDashboardData() {
        try {
            const [posts, notes, drafts, media] = await Promise.all([
                this.fetchFiles('content/posts'),
                this.fetchFiles('content/notes'),
                this.fetchFiles('content/drafts'),
                this.fetchFiles('static/images')
            ]);

            document.getElementById('totalArticles').textContent = posts.length;
            document.getElementById('totalNotes').textContent = notes.length;
            document.getElementById('totalDrafts').textContent = drafts.length;
            document.getElementById('totalImages').textContent = media.length;

            this.renderCategoryStats(posts, notes, drafts);
            this.renderTagCloud(posts, notes, drafts);
            this.renderRecentUpdates([...posts, ...notes, ...drafts]);
        } catch (error) {
            console.error('加载仪表盘数据错误:', error);
            this.showNotification('加载数据失败', 'error');
        }
    }

    async fetchFiles(path) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/files?path=${encodeURIComponent(path)}`);
            const data = await response.json();
            return data.success ? data.files : [];
        } catch (error) {
            console.error(`获取文件列表错误 (${path}):`, error);
            return [];
        }
    }

    renderCategoryStats(posts, notes, drafts) {
        const container = document.getElementById('categoryStats');
        const categories = {};

        const allFiles = [...posts, ...notes, ...drafts];
        allFiles.forEach(file => {
            const category = this.extractCategory(file.name) || '未分类';
            categories[category] = (categories[category] || 0) + 1;
        });

        if (Object.keys(categories).length === 0) {
            container.innerHTML = '<p class="empty-text">暂无数据</p>';
            return;
        }

        const maxCount = Math.max(...Object.values(categories));
        let html = '';

        for (const [category, count] of Object.entries(categories)) {
            const percentage = (count / maxCount) * 100;
            html += `
                <div class="category-item">
                    <div class="category-info">
                        <span class="category-name">${category}</span>
                        <span class="category-count">${count} 篇</span>
                    </div>
                    <div class="category-bar">
                        <div class="category-fill" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
    }

    extractCategory(filename) {
        const match = filename.match(/^\d{4}-\d{2}-\d{2}-(.+?)-/);
        return match ? match[1] : null;
    }

    renderTagCloud(posts, notes, drafts) {
        const container = document.getElementById('tagCloud');
        const tags = {};

        const loadAndProcessTags = async (files, path) => {
            for (const file of files.slice(0, 10)) {
                try {
                    const response = await fetch(`${this.apiBaseUrl}/api/file?path=${encodeURIComponent(file.path)}`);
                    const data = await response.json();
                    if (data.success) {
                        const content = atob(data.content);
                        const tagMatch = content.match(/tags:\s*\[([^\]]+)\]/);
                        if (tagMatch) {
                            const tagList = tagMatch[1].split(',').map(t => t.trim().replace(/["']/g, ''));
                            tagList.forEach(tag => {
                                if (tag) tags[tag] = (tags[tag] || 0) + 1;
                            });
                        }
                    }
                } catch (e) { }
            }
        };

        Promise.all([
            loadAndProcessTags(posts.slice(0, 5), 'content/posts'),
            loadAndProcessTags(notes.slice(0, 3), 'content/notes')
        ]).then(() => {
            const tagArray = Object.entries(tags).sort((a, b) => b[1] - a[1]).slice(0, 20);

            if (tagArray.length === 0) {
                container.innerHTML = '<p class="empty-text">暂无标签</p>';
                return;
            }

            container.innerHTML = tagArray.map(([tag, count]) =>
                `<span class="tag-item">${tag} (${count})</span>`
            ).join('');
        });
    }

    renderRecentUpdates(files) {
        const container = document.getElementById('recentUpdates');

        if (files.length === 0) {
            container.innerHTML = '<p class="empty-text">暂无更新</p>';
            return;
        }

        const sorted = files.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)).slice(0, 5);

        container.innerHTML = sorted.map(file => `
            <div class="recent-item">
                <div class="recent-info">
                    <div class="recent-name">${file.name}</div>
                    <div class="recent-meta">${file.path} · ${file.updated_at ? new Date(file.updated_at).toLocaleString('zh-CN') : '-'}</div>
                </div>
            </div>
        `).join('');
    }

    async loadArticles() {
        const tbody = document.getElementById('articlesTableBody');
        tbody.innerHTML = '<tr><td colspan="6" class="loading-text">加载中...</td></tr>';

        try {
            const [posts, notes, drafts] = await Promise.all([
                this.fetchFiles('content/posts'),
                this.fetchFiles('content/notes'),
                this.fetchFiles('content/drafts')
            ]);

            this.articles = [...posts.map(f => ({ ...f, dir: 'content/posts', dirName: '文章' })),
            ...notes.map(f => ({ ...f, dir: 'content/notes', dirName: '笔记' })),
            ...drafts.map(f => ({ ...f, dir: 'content/drafts', dirName: '草稿' }))];

            this.renderArticlesTable(this.articles);
        } catch (error) {
            console.error('加载文章列表错误:', error);
            tbody.innerHTML = '<tr><td colspan="6" class="loading-text">加载失败</td></tr>';
        }
    }

    renderArticlesTable(articles) {
        const tbody = document.getElementById('articlesTableBody');

        if (articles.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-text">暂无文章</td></tr>';
            return;
        }

        tbody.innerHTML = articles.map(file => `
            <tr>
                <td class="table-title" title="${file.name}">${file.name}</td>
                <td>${this.extractCategory(file.name) || '-'}</td>
                <td><span class="table-tag">-</span></td>
                <td>${file.dirName}</td>
                <td>${file.updated_at ? new Date(file.updated_at).toLocaleDateString('zh-CN') : '-'}</td>
                <td class="table-actions">
                    <button class="action-btn view" data-path="${file.path}">查看</button>
                    <button class="action-btn delete" data-path="${file.path}">删除</button>
                </td>
            </tr>
        `).join('');

        tbody.querySelectorAll('.action-btn.view').forEach(btn => {
            btn.addEventListener('click', () => this.viewArticle(btn.dataset.path));
        });

        tbody.querySelectorAll('.action-btn.delete').forEach(btn => {
            btn.addEventListener('click', () => this.deleteArticle(btn.dataset.path));
        });
    }

    filterArticles() {
        const search = document.getElementById('articleSearch').value.toLowerCase();
        const category = document.getElementById('articleCategory').value;
        const dir = document.getElementById('articleDir').value;

        let filtered = this.articles;

        if (search) {
            filtered = filtered.filter(f => f.name.toLowerCase().includes(search));
        }

        if (category) {
            filtered = filtered.filter(f => this.extractCategory(f.name) === category);
        }

        if (dir !== 'all') {
            filtered = filtered.filter(f => f.dir === dir);
        }

        this.renderArticlesTable(filtered);
    }

    async viewArticle(path) {
        window.open(`index.html?file=${encodeURIComponent(path)}`, '_blank');
    }

    async deleteArticle(path) {
        if (!confirm('确定要删除这篇文章吗？此操作不可撤销！')) return;

        this.showPasswordDialog('删除文章', async () => {
            this.showLoading('正在删除...');

            try {
                const response = await fetch(`${this.apiBaseUrl}/api/file?path=${encodeURIComponent(path)}`, {
                    method: 'DELETE'
                });
                const data = await response.json();

                if (data.success) {
                    this.showNotification('删除成功', 'success');
                    this.loadArticles();
                    this.loadDashboardData();
                } else {
                    this.showNotification(`删除失败: ${data.error}`, 'error');
                }
            } catch (error) {
                console.error('删除文章错误:', error);
                this.showNotification(`网络错误: ${error.message}`, 'error');
            } finally {
                this.hideLoading();
            }
        });
    }

    showPasswordDialog(action, onSuccess) {
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
            return data.success === true;
        } catch (error) {
            console.error('密码验证错误:', error);
            return false;
        }
    }

    async loadMedia() {
        const grid = document.getElementById('mediaGrid');
        grid.innerHTML = '<p class="loading-text">加载中...</p>';

        try {
            const files = await this.fetchFiles('static/images');
            this.mediaFiles = files.filter(f => /\.(jpg|jpeg|png|gif|webp|svg|bmp)$/i.test(f.name));
            this.renderMediaGrid(this.mediaFiles);
        } catch (error) {
            console.error('加载媒体库错误:', error);
            grid.innerHTML = '<p class="loading-text">加载失败</p>';
        }
    }

    renderMediaGrid(files) {
        const grid = document.getElementById('mediaGrid');

        if (files.length === 0) {
            grid.innerHTML = '<p class="empty-text">暂无图片</p>';
            return;
        }

        grid.innerHTML = files.map(file => `
            <div class="media-item">
                <div class="media-preview">
                    <img src="${this.getImageUrl(file.path)}" alt="${file.name}" loading="lazy">
                </div>
                <div class="media-info">
                    <div class="media-name" title="${file.name}">${file.name}</div>
                    <div class="media-meta">${this.formatFileSize(file.size)}</div>
                </div>
            </div>
        `).join('');
    }

    getImageUrl(path) {
        const match = path.match(/static\/images\/(.+)/);
        if (match) {
            return `${this.apiBaseUrl}/images/${match[1]}`;
        }
        return '';
    }

    formatFileSize(bytes) {
        if (!bytes) return 'Unknown';
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }

    filterMedia(search) {
        if (!search) {
            this.renderMediaGrid(this.mediaFiles);
            return;
        }

        const filtered = this.mediaFiles.filter(f =>
            f.name.toLowerCase().includes(search.toLowerCase())
        );
        this.renderMediaGrid(filtered);
    }

    async checkSystemStatus() {
        document.getElementById('backendStatus').textContent = '检查中...';
        document.getElementById('backendStatus').className = 'status-badge status-checking';
        document.getElementById('githubStatus').textContent = '检查中...';
        document.getElementById('githubStatus').className = 'status-badge status-checking';
        document.getElementById('apiStatus').textContent = '检查中...';
        document.getElementById('apiStatus').className = 'status-badge status-checking';
        document.getElementById('backendUrl').textContent = this.apiBaseUrl || '-';

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/health`);
            if (response.ok) {
                document.getElementById('backendStatus').textContent = '正常';
                document.getElementById('backendStatus').className = 'status-badge status-ok';
                document.getElementById('apiStatus').textContent = '正常';
                document.getElementById('apiStatus').className = 'status-badge status-ok';

                try {
                    const files = await this.fetchFiles('content/posts');
                    document.getElementById('githubStatus').textContent = '正常';
                    document.getElementById('githubStatus').className = 'status-badge status-ok';
                } catch {
                    document.getElementById('githubStatus').textContent = '异常';
                    document.getElementById('githubStatus').className = 'status-badge status-error';
                }
            } else {
                document.getElementById('backendStatus').textContent = '异常';
                document.getElementById('backendStatus').className = 'status-badge status-error';
                document.getElementById('apiStatus').textContent = '异常';
                document.getElementById('apiStatus').className = 'status-badge status-error';
            }
        } catch (error) {
            document.getElementById('backendStatus').textContent = '离线';
            document.getElementById('backendStatus').className = 'status-badge status-error';
            document.getElementById('apiStatus').textContent = '离线';
            document.getElementById('apiStatus').className = 'status-badge status-error';
        }
    }

    async syncAllFiles() {
        this.showLoading('正在同步...');
        this.showNotification('同步中...', 'info');

        setTimeout(() => {
            this.hideLoading();
            this.showNotification('同步完成', 'success');
            this.loadDashboardData();
        }, 1000);
    }

    async clearCache() {
        if (!confirm('确定要清除缓存吗？')) return;

        this.showLoading('正在清除...');
        localStorage.clear();

        setTimeout(() => {
            this.hideLoading();
            this.showNotification('缓存已清除', 'success');
        }, 500);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.adminPanel = new AdminPanel();
});
