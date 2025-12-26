class ArticleBrowser {
    constructor() {
        this.apiBaseUrl = window.APP_CONFIG?.apiBaseUrl || '';
        this.articles = [];
        this.currentPath = null;

        this.initElements();
        this.bindEvents();
        this.loadArticles();
    }

    initElements() {
        this.searchInput = document.getElementById('searchInput');
        this.dirFilter = document.getElementById('dirFilter');
        this.articleList = document.getElementById('articleList');
        this.articleCount = document.getElementById('articleCount');
        this.refreshListBtn = document.getElementById('refreshListBtn');

        this.contentPlaceholder = document.getElementById('contentPlaceholder');
        this.articleContent = document.getElementById('articleContent');
        this.articleTitle = document.getElementById('articleTitle');
        this.articleDate = document.getElementById('articleDate');
        this.articleCategory = document.getElementById('articleCategory');
        this.articleTags = document.getElementById('articleTags');
        this.articleBody = document.getElementById('articleBody');

        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.loadingText = document.getElementById('loadingText');
    }

    bindEvents() {
        this.refreshListBtn.addEventListener('click', () => this.loadArticles());
        this.searchInput.addEventListener('input', () => this.filterArticles());
        this.dirFilter.addEventListener('change', () => this.loadArticles());
    }

    showLoading(message = '加载中...') {
        this.loadingText.textContent = message;
        this.loadingOverlay.classList.remove('hidden');
    }

    hideLoading() {
        this.loadingOverlay.classList.add('hidden');
    }

    async loadArticles() {
        const selectedDir = this.dirFilter.value;
        this.articleList.innerHTML = '<p class="loading-text">加载中...</p>';

        try {
            if (selectedDir === 'all') {
                const [posts, notes, drafts] = await Promise.all([
                    this.fetchFiles('content/posts'),
                    this.fetchFiles('content/notes'),
                    this.fetchFiles('content/drafts')
                ]);
                this.articles = [
                    ...posts.map(f => ({ ...f, dir: 'content/posts', dirName: '文章' })),
                    ...notes.map(f => ({ ...f, dir: 'content/notes', dirName: '笔记' })),
                    ...drafts.map(f => ({ ...f, dir: 'content/drafts', dirName: '草稿' }))
                ];
            } else {
                const dirNames = {
                    'content/posts': '文章',
                    'content/notes': '笔记',
                    'content/drafts': '草稿'
                };
                const files = await this.fetchFiles(selectedDir);
                this.articles = files.map(f => ({ ...f, dir: selectedDir, dirName: dirNames[selectedDir] }));
            }

            // 按更新时间排序
            this.articles.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
            this.filterArticles();
        } catch (error) {
            console.error('加载文章错误:', error);
            this.articleList.innerHTML = '<p class="empty-text">加载失败</p>';
        }
    }

    async fetchFiles(path) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/files?path=${encodeURIComponent(path)}`);
            const data = await response.json();
            return data.success ? data.files : [];
        } catch (error) {
            console.error(`获取文件错误 (${path}):`, error);
            return [];
        }
    }

    filterArticles() {
        const keyword = this.searchInput.value.toLowerCase().trim();
        let filtered = this.articles;

        if (keyword) {
            filtered = filtered.filter(f => f.name.toLowerCase().includes(keyword));
        }

        this.renderArticleList(filtered);
    }

    renderArticleList(articles) {
        if (articles.length === 0) {
            this.articleList.innerHTML = '<p class="empty-text">暂无文章</p>';
            this.articleCount.textContent = '0 篇文章';
            return;
        }

        this.articleList.innerHTML = articles.map(f => {
            const date = f.updated_at ? new Date(f.updated_at).toLocaleDateString('zh-CN') : '';
            const isActive = this.currentPath === f.path;
            return `
                <div class="article-list-item${isActive ? ' active' : ''}" data-path="${f.path}">
                    <div class="item-content">
                        <div class="item-title" title="${f.name}">${f.name.replace('.md', '')}</div>
                        <div class="item-meta">
                            <span class="item-dir">${f.dirName}</span>
                            <span>${date}</span>
                        </div>
                    </div>
                    <button class="item-delete-btn" data-path="${f.path}" data-name="${f.name}" title="删除">×</button>
                </div>
            `;
        }).join('');

        this.articleCount.textContent = `${articles.length} 篇文章`;

        this.articleList.querySelectorAll('.item-content').forEach(item => {
            item.addEventListener('click', () => {
                const path = item.parentElement.dataset.path;
                this.selectArticle(path);
            });
        });

        this.articleList.querySelectorAll('.item-delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const path = btn.dataset.path;
                const name = btn.dataset.name;
                this.confirmDeleteArticle(path, name);
            });
        });
    }

    selectArticle(path) {
        this.currentPath = path;

        // 更新选中状态
        this.articleList.querySelectorAll('.article-list-item').forEach(item => {
            item.classList.toggle('active', item.dataset.path === path);
        });

        this.loadArticleContent(path);
    }

    async loadArticleContent(path) {
        this.showLoading('加载文章...');

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/file?path=${encodeURIComponent(path)}`);
            const data = await response.json();

            if (data.success) {
                // API 已返回解码后的 UTF-8 文本，直接使用
                this.displayArticle(data.content);
            } else {
                this.articleBody.innerHTML = `<p class="empty-text">加载失败: ${data.error}</p>`;
            }
        } catch (error) {
            console.error('加载文章错误:', error);
            this.articleBody.innerHTML = `<p class="empty-text">网络错误: ${error.message}</p>`;
        } finally {
            this.hideLoading();
        }
    }

    displayArticle(content) {
        const { frontMatter, body } = this.parseFrontMatter(content);

        this.articleTitle.textContent = frontMatter.title || '无标题';
        this.articleDate.textContent = frontMatter.date ? `📅 ${frontMatter.date}` : '';
        this.articleCategory.textContent = frontMatter.categories?.length ? `📁 ${frontMatter.categories.join(', ')}` : '';
        this.articleTags.textContent = frontMatter.tags?.length ? `🏷️ ${frontMatter.tags.join(', ')}` : '';

        this.articleBody.innerHTML = this.renderMarkdown(body);

        this.contentPlaceholder.classList.add('hidden');
        this.articleContent.classList.remove('hidden');
    }

    parseFrontMatter(content) {
        const result = {
            frontMatter: { title: '', date: '', categories: [], tags: [] },
            body: content
        };

        const lines = content.split('\n');
        let inFrontMatter = false;
        let frontMatterEnd = 0;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();

            if (line === '---') {
                if (!inFrontMatter) {
                    inFrontMatter = true;
                    continue;
                } else {
                    frontMatterEnd = i;
                    break;
                }
            }

            if (inFrontMatter && line.includes(':')) {
                const colonIndex = line.indexOf(':');
                const key = line.slice(0, colonIndex).trim();
                const value = line.slice(colonIndex + 1).trim();

                if (key === 'title') {
                    result.frontMatter.title = value.replace(/^["']|["']$/g, '');
                } else if (key === 'date') {
                    result.frontMatter.date = value.split('T')[0];
                } else if (key === 'categories' || key === 'tags') {
                    const match = value.match(/\[([^\]]*)\]/);
                    if (match) {
                        result.frontMatter[key] = match[1].split(',').map(t => t.trim().replace(/["']/g, '')).filter(t => t);
                    }
                }
            }
        }

        if (frontMatterEnd > 0) {
            result.body = lines.slice(frontMatterEnd + 1).join('\n').trim();
        }

        return result;
    }

    renderMarkdown(markdown) {
        let html = markdown
            .replace(/^### (.+)$/gm, '<h3>$1</h3>')
            .replace(/^## (.+)$/gm, '<h2>$1</h2>')
            .replace(/^# (.+)$/gm, '<h1>$1</h1>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/```(\w+)?\n([\s\S]+?)```/g, '<pre><code class="language-$1">$2</code></pre>')
            .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>')
            .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
            .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1">')
            .replace(/^- (.+)$/gm, '<li>$1</li>')
            .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/^(?!<[hpulob])(.+)$/gm, '<p>$1</p>');

        // 处理列表包装
        html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`);

        // 合并连续的 blockquote
        html = html.replace(/<\/blockquote>\s*<blockquote>/g, '<br>');

        return html;
    }

    confirmDeleteArticle(path, name) {
        if (!confirm(`确定要删除文章 "${name}" 吗？\n\n此操作不可撤销！`)) return;

        this.showPasswordDialog('删除文章', async () => {
            await this.deleteArticle(path, name);
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

    async deleteArticle(path, name) {
        this.showLoading('正在删除...');

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/file?path=${encodeURIComponent(path)}`, {
                method: 'DELETE'
            });
            const data = await response.json();

            if (data.success) {
                alert('删除成功！');
                this.loadArticles();
                this.contentPlaceholder.classList.remove('hidden');
                this.articleContent.classList.add('hidden');
            } else {
                alert(`删除失败: ${data.error}`);
            }
        } catch (error) {
            console.error('删除文章错误:', error);
            alert(`网络错误: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.browser = new ArticleBrowser();
});
