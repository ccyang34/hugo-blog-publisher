class ArticleBrowser {
    constructor() {
        this.apiBaseUrl = window.APP_CONFIG?.apiBaseUrl || '';
        this.articles = [];
        this.filteredArticles = [];
        this.articleDates = {}; // 存储文章日期
        this.currentPath = null;
        this.sortMode = 'date'; // 'date' 或 'name'
        this.currentPage = 1;
        this.pageSize = 20;
        this.isLoadingMore = false;
        this.hasMoreArticles = true;

        this.initElements();
        this.bindEvents();
        this.setupInfiniteScroll();

        // 检查是否有会话授权
        if (sessionStorage.getItem('hugo_authenticated') === 'true') {
            this.loadArticles();
        } else {
            this.handleAccessValidation();
        }
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

        // Elements for mobile view
        this.articleListPanel = document.querySelector('.article-list-panel');
        this.articleContentPanel = document.getElementById('articleContentPanel');
        this.backToListBtn = document.getElementById('backToListBtn');

        // Elements for File Browser
        this.tabBtns = document.querySelectorAll('.tab-btn');
        this.sectionArticles = document.querySelectorAll('.section-articles');
        this.sectionFiles = document.querySelectorAll('.section-files');
        this.fileList = document.getElementById('fileList');
        this.refreshFilesBtn = document.getElementById('refreshFilesBtn');
        this.uploadFileBtn = document.getElementById('uploadFileBtn');
        this.navUpBtn = document.getElementById('navUpBtn');
        this.currentPathEl = document.getElementById('currentPath');

        // File browser state
        this.currentBrowsePath = 'static';
    }

    bindEvents() {
        this.refreshListBtn.addEventListener('click', () => this.loadArticles());
        this.searchInput.addEventListener('input', () => this.filterArticles());
        this.dirFilter.addEventListener('change', () => this.loadArticles());

        document.getElementById('sortBtn')?.addEventListener('click', () => this.toggleSort());

        // Mobile navigation event
        if (this.backToListBtn) {
            this.backToListBtn.addEventListener('click', () => this.showListPanel());
        }

        // Tab Switching
        this.tabBtns.forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });

        // File Browser Events
        this.refreshFilesBtn?.addEventListener('click', () => this.loadFiles());
        this.uploadFileBtn?.addEventListener('click', () => this.showUploadDialog());
        this.navUpBtn?.addEventListener('click', () => this.navigateUp());

        // Delegate for content body images (preview)
        this.articleBody.addEventListener('click', (e) => {
            if (e.target.tagName === 'IMG') {
                this.showImagePreview(e.target.src);
            }
        });
    }

    switchTab(tab) {
        this.tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });

        if (tab === 'articles') {
            this.sectionArticles.forEach(el => el.classList.remove('hidden'));
            this.sectionFiles.forEach(el => el.classList.add('hidden'));
        } else {
            this.sectionArticles.forEach(el => el.classList.add('hidden'));
            this.sectionFiles.forEach(el => el.classList.remove('hidden'));
            this.loadFiles();
        }
    }

    async loadFiles() {
        this.fileList.innerHTML = '<p class="loading-text">加载文件中...</p>';
        this.currentPathEl.textContent = this.currentBrowsePath + '/';

        // 禁用返回按钮如果在根目录
        this.navUpBtn.disabled = (this.currentBrowsePath === 'static');

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/files?path=${encodeURIComponent(this.currentBrowsePath)}`);
            const data = await response.json();

            if (data.success && data.files) {
                this.renderFiles(data.files);
            } else {
                this.fileList.innerHTML = `<p class="empty-text">加载失败: ${data.error || '原因未知'}</p>`;
            }
        } catch (error) {
            console.error('加载文件错误:', error);
            this.fileList.innerHTML = '<p class="empty-text">网络错误</p>';
        }
    }

    renderFiles(files) {
        if (files.length === 0) {
            this.fileList.innerHTML = '<p class="empty-text">暂无文件</p>';
            return;
        }

        // 排序：文件夹在前，文件在后
        files.sort((a, b) => {
            if (a.is_dir && !b.is_dir) return -1;
            if (!a.is_dir && b.is_dir) return 1;
            return a.name.localeCompare(b.name, 'zh-CN');
        });

        this.fileList.innerHTML = files.map(file => {
            const isImage = /\.(png|jpg|jpeg|gif|webp|svg|bmp|ico)$/i.test(file.name);
            const isDir = file.is_dir;
            const icon = isDir ? '📁' : (isImage ? '🖼️' : '📄');
            const url = file.url || `${this.apiBaseUrl}/${file.path}`;

            return `
                <div class="file-item ${isDir ? 'is-folder' : ''}" data-path="${file.path}" data-name="${file.name}" data-is-dir="${isDir}" data-url="${url}">
                    <div class="file-icon">${icon}</div>
                    <div class="file-info">
                        <div class="file-name" title="${file.name}">${file.name}</div>
                        ${!isDir && file.size ? `<div class="file-size">${this.formatFileSize(file.size)}</div>` : ''}
                    </div>
                    <div class="file-actions">
                        ${!isDir ? `<button class="file-action-btn download-btn" title="下载">⬇️</button>` : ''}
                        <button class="file-action-btn rename-btn" title="重命名">✏️</button>
                        <button class="file-action-btn delete-btn" title="删除">🗑️</button>
                    </div>
                </div>
            `;
        }).join('');

        // 绑定事件
        this.fileList.querySelectorAll('.file-item').forEach(item => {
            const path = item.dataset.path;
            const name = item.dataset.name;
            const isDir = item.dataset.isDir === 'true';
            const url = item.dataset.url;

            // 点击进入文件夹或预览图片
            item.addEventListener('click', (e) => {
                if (e.target.closest('.file-actions')) return;
                if (isDir) {
                    this.navigateToFolder(path);
                } else if (/\.(png|jpg|jpeg|gif|webp|svg|bmp|ico)$/i.test(name)) {
                    this.showImagePreview(url);
                }
            });

            // 删除按钮
            item.querySelector('.delete-btn')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.confirmDeleteFile(path, name);
            });

            // 重命名按钮
            item.querySelector('.rename-btn')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showRenameDialog(path, name);
            });

            // 下载按钮
            item.querySelector('.download-btn')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.downloadFile(url, name);
            });
        });
    }

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    navigateToFolder(path) {
        this.currentBrowsePath = path;
        this.loadFiles();
    }

    navigateUp() {
        if (this.currentBrowsePath === 'static') return;
        const parts = this.currentBrowsePath.split('/');
        parts.pop();
        this.currentBrowsePath = parts.join('/') || 'static';
        this.loadFiles();
    }

    confirmDeleteFile(path, name) {
        if (confirm(`确定要永久删除 "${name}" 吗？\n\n此操作不可撤销！`)) {
            this.deleteFile(path);
        }
    }

    async deleteFile(path) {
        this.showLoading('正在删除...');
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/file?path=${encodeURIComponent(path)}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            if (data.success) {
                this.loadFiles();
            } else {
                alert(`删除失败: ${data.error}`);
            }
        } catch (error) {
            console.error('删除文件错误:', error);
            alert('删除请求失败');
        } finally {
            this.hideLoading();
        }
    }

    downloadFile(url, name) {
        const a = document.createElement('a');
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    showRenameDialog(path, oldName) {
        const newName = prompt('请输入新的文件名：', oldName);
        if (newName && newName !== oldName) {
            this.renameFile(path, newName);
        }
    }

    async renameFile(oldPath, newName) {
        this.showLoading('正在重命名...');
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/rename`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_path: oldPath, new_name: newName })
            });
            const data = await response.json();
            if (data.success) {
                this.loadFiles();
            } else {
                alert(`重命名失败: ${data.error}`);
            }
        } catch (error) {
            console.error('重命名错误:', error);
            alert('重命名请求失败');
        } finally {
            this.hideLoading();
        }
    }

    showUploadDialog() {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.onchange = async (e) => {
            const files = e.target.files;
            if (files.length > 0) {
                await this.uploadFiles(files);
            }
        };
        input.click();
    }

    async uploadFiles(files) {
        this.showLoading(`正在上传 ${files.length} 个文件...`);
        try {
            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('path', this.currentBrowsePath);

                const response = await fetch(`${this.apiBaseUrl}/api/upload`, {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                if (!data.success) {
                    alert(`上传 ${file.name} 失败: ${data.error}`);
                }
            }
            this.loadFiles();
        } catch (error) {
            console.error('上传错误:', error);
            alert('上传请求失败');
        } finally {
            this.hideLoading();
        }
    }

    showImagePreview(src) {
        const overlay = document.createElement('div');
        overlay.className = 'image-preview-overlay';
        overlay.innerHTML = `<img src="${src}" alt="Preview">`;
        overlay.onclick = () => overlay.remove();
        document.body.appendChild(overlay);

        // Escape to close
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                overlay.remove();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
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

            // 默认按文件名排序（待日期加载后重新排序）
            this.sortArticles();
            this.filterArticles();
        } catch (error) {
            console.error('加载文章错误:', error);
            this.articleList.innerHTML = '<p class="empty-text">加载失败</p>';
        }
    }

    async fetchFiles(path) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/files?path=${encodeURIComponent(path)}&fetch_metadata=true`);
            const data = await response.json();
            if (data.success) {
                // 批量存储抓取到的日期数据
                if (data.files) {
                    data.files.forEach(f => {
                        if (f.updated_at) {
                            this.articleDates[f.path] = new Date(f.updated_at).getTime();
                        }
                    });
                }
                return data.files;
            }
            return [];
        } catch (error) {
            console.error(`获取文件错误 (${path}):`, error);
            return [];
        }
    }

    sortArticles() {
        if (this.sortMode === 'name') {
            // 按文件名排序（A-Z）
            this.articles.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
        } else {
            // 按日期排序（新到旧）
            this.articles.sort((a, b) => {
                const dateA = this.articleDates[a.path] || 0;
                const dateB = this.articleDates[b.path] || 0;
                return dateB - dateA;
            });
        }
    }

    toggleSort() {
        this.sortMode = this.sortMode === 'date' ? 'name' : 'date';
        this.sortArticles();
        this.filterArticles();
        this.updateSortButton();
    }

    updateSortButton() {
        const sortBtn = document.getElementById('sortBtn');
        if (sortBtn) {
            sortBtn.textContent = this.sortMode === 'date' ? '📅 时间' : '📝 文件名';
            sortBtn.title = this.sortMode === 'date' ? '当前按时间排序，点击切换' : '当前按文件名排序，点击切换';
        }
    }

    filterArticles() {
        const keyword = this.searchInput.value.toLowerCase().trim();
        this.filteredArticles = this.articles;

        if (keyword) {
            this.filteredArticles = this.filteredArticles.filter(f => f.name.toLowerCase().includes(keyword));
        }

        this.currentPage = 1; // 重置到第一页
        this.renderCurrentPage();
    }

    renderCurrentPage() {
        const start = (this.currentPage - 1) * this.pageSize;
        const end = start + this.pageSize;
        const pageArticles = this.filteredArticles.slice(start, end);

        this.renderArticleList(pageArticles);
        this.renderPagination();
    }

    renderPagination() {
        // 瀑布流模式：不显示翻页按钮，只显示文章计数和加载提示
        const footer = document.querySelector('.list-footer');
        const totalPages = Math.ceil(this.filteredArticles.length / this.pageSize);
        const loadingHint = this.currentPage < totalPages ? '<span class="load-more-hint">↓ 下滑加载更多</span>' : '<span class="load-more-hint">已加载全部</span>';
        footer.innerHTML = `
            <span id="articleCount">${this.filteredArticles.length} 篇文章</span>
            ${loadingHint}
        `;
        this.hasMoreArticles = this.currentPage < totalPages;
    }

    setupInfiniteScroll() {
        // 监听文章列表容器的滚动事件（#articleList 是实际有滚动条的元素）
        const listContainer = document.getElementById('articleList');
        if (!listContainer) return;

        listContainer.addEventListener('scroll', () => {
            if (this.isLoadingMore || !this.hasMoreArticles) return;

            const scrollTop = listContainer.scrollTop;
            const scrollHeight = listContainer.scrollHeight;
            const clientHeight = listContainer.clientHeight;

            // 当滚动到底部 100px 范围内时加载更多
            if (scrollTop + clientHeight >= scrollHeight - 100) {
                this.loadMoreArticles();
            }
        });
    }

    loadMoreArticles() {
        const totalPages = Math.ceil(this.filteredArticles.length / this.pageSize);
        if (this.currentPage >= totalPages) {
            this.hasMoreArticles = false;
            return;
        }

        this.isLoadingMore = true;
        this.currentPage++;

        const start = (this.currentPage - 1) * this.pageSize;
        const end = start + this.pageSize;
        const moreArticles = this.filteredArticles.slice(start, end);

        // 追加文章到列表
        this.appendArticles(moreArticles);
        this.renderPagination();

        this.isLoadingMore = false;
    }

    appendArticles(articles) {
        if (articles.length === 0) return;

        const html = articles.map(f => {
            const isActive = this.currentPath === f.path;
            return `
                <div class="article-list-item${isActive ? ' active' : ''}" data-path="${f.path}">
                    <div class="item-content">
                        <div class="item-title" title="${f.name}">${f.name.replace('.md', '')}</div>
                        <div class="item-meta">
                            <span class="item-dir">${f.dirName}</span>
                            <span class="item-date" data-path="${f.path}">加载中...</span>
                        </div>
                    </div>
                    <button class="item-delete-btn" data-path="${f.path}" data-name="${f.name}" title="删除">×</button>
                </div>
            `;
        }).join('');

        this.articleList.insertAdjacentHTML('beforeend', html);

        // 更新日期显示
        articles.forEach(f => {
            const dateVal = this.articleDates[f.path];
            const dateSpan = this.articleList.querySelector(`.item-date[data-path="${f.path}"]`);
            if (dateSpan) {
                if (dateVal) {
                    const date = new Date(dateVal);
                    dateSpan.textContent = date.toLocaleString('zh-CN', {
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                    });
                } else {
                    dateSpan.textContent = '-';
                }
            }
        });

        // 绑定事件
        const newItems = this.articleList.querySelectorAll('.article-list-item:not([data-bound])');
        newItems.forEach(item => {
            item.setAttribute('data-bound', 'true');
            item.querySelector('.item-content').addEventListener('click', () => {
                this.selectArticle(item.dataset.path);
            });
            item.querySelector('.item-delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.confirmDeleteArticle(item.dataset.path, item.querySelector('.item-delete-btn').dataset.name);
            });
        });
    }

    renderArticleList(articles) {
        if (articles.length === 0) {
            this.articleList.innerHTML = '<p class="empty-text">暂无文章</p>';
            this.articleCount.textContent = '0 篇文章';
            return;
        }

        this.articleList.innerHTML = articles.map(f => {
            const isActive = this.currentPath === f.path;
            return `
                <div class="article-list-item${isActive ? ' active' : ''}" data-path="${f.path}">
                    <div class="item-content">
                        <div class="item-title" title="${f.name}">${f.name.replace('.md', '')}</div>
                        <div class="item-meta">
                            <span class="item-dir">${f.dirName}</span>
                            <span class="item-date" data-path="${f.path}">加载中...</span>
                        </div>
                    </div>
                    <button class="item-delete-btn" data-path="${f.path}" data-name="${f.name}" title="删除">×</button>
                </div>
            `;
        }).join('');

        this.articleCount.textContent = `${articles.length} 篇文章`;

        // 更新日期显示
        articles.forEach(f => {
            const dateVal = this.articleDates[f.path];
            const dateSpan = this.articleList.querySelector(`.item-date[data-path="${f.path}"]`);
            if (dateSpan) {
                if (dateVal) {
                    const date = new Date(dateVal);
                    dateSpan.textContent = date.toLocaleString('zh-CN', {
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                    });
                } else {
                    dateSpan.textContent = '-';
                }
            }
        });

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

    async loadArticleDate(path) {
        // 此方法已由 fetchFiles 中的并发抓取逻辑替代，保持为空以兼容旧调用（如果存在）
    }

    selectArticle(path) {
        this.currentPath = path;

        // 更新选中状态
        this.articleList.querySelectorAll('.article-list-item').forEach(item => {
            item.classList.toggle('active', item.dataset.path === path);
        });

        this.loadArticleContent(path);

        // Mobile: Show content panel
        this.showContentPanel();
    }

    showContentPanel() {
        // Only active on mobile view width
        if (window.innerWidth <= 768) {
            this.articleListPanel.classList.add('hidden-mobile');
            this.articleContentPanel.classList.add('active-mobile');
            // Hide placeholder on mobile to ensure content is visible
            if (this.contentPlaceholder) this.contentPlaceholder.classList.add('hidden');
        }
    }

    showListPanel() {
        this.articleListPanel.classList.remove('hidden-mobile');
        this.articleContentPanel.classList.remove('active-mobile');
        this.currentPath = null;
        // Reset active state
        this.articleList.querySelectorAll('.article-list-item').forEach(item => {
            item.classList.remove('active');
        });
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
            .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
                const fallbackAttr = src.startsWith('/images/') ? `onerror="if(!this.dataset.tried){this.dataset.tried=true; this.src=this.src.replace('/images/', 'https://raw.githubusercontent.com/${window.APP_CONFIG?.githubUser}/${window.APP_CONFIG?.githubRepo}/main/static/images/');}"` : '';
                return `<img src="${src}" alt="${alt}" ${fallbackAttr}>`;
            })
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
        if (confirm(`确定要删除文章 "${name}" 吗？\n\n此操作不可撤销！`)) {
            this.deleteArticle(path, name);
        }
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
                // Return to list view on mobile
                this.showListPanel();
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

    handleAccessValidation() {
        // 清空列表显示
        if (this.articleList) {
            this.articleList.innerHTML = '<p class="empty-text">需要密码验证才能浏览文章</p>';
        }
        this.showPasswordDialog('进入浏览页面', () => {
            this.loadArticles();
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.browser = new ArticleBrowser();
});
