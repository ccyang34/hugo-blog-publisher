/**
 * 前端公共工具模块
 * - markdownToHtml: 安全的 Markdown 渲染（HTML 转义防 XSS）
 * - apiFetch: 统一 API 请求（自动携带令牌、统一 401 处理）
 * - 认证辅助: isAuthenticated / clearSession
 */
(function (global) {
    'use strict';

    const TOKEN_KEY = 'hugo_publish_token';
    const AUTH_KEY = 'hugo_authenticated';

    function escapeHtml(str) {
        return String(str == null ? '' : str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    /** 只允许安全的 URL 协议（http/https/相对路径），其余返回 '#' 防止 javascript: 注入 */
    function sanitizeUrl(url) {
        const value = String(url == null ? '' : url).trim();
        if (/^(https?:)?\/\//i.test(value) || value.startsWith('/') || /^data:image\//i.test(value)) {
            return value;
        }
        return '#';
    }

    /**
     * 安全的 Markdown → HTML 渲染
     * 先对原文做 HTML 转义（原始内容中的 <script>、onerror 等不会执行），再应用白名单语法转换
     */
    function markdownToHtml(markdown) {
        // 1. HTML 转义：防止原始内容注入 HTML/脚本（XSS 关键步骤）
        let html = escapeHtml(markdown);

        // 2. 白名单 Markdown 语法转换
        html = html
            .replace(/^### (.+)$/gm, '<h3>$1</h3>')
            .replace(/^## (.+)$/gm, '<h2>$1</h2>')
            .replace(/^# (.+)$/gm, '<h1>$1</h1>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`(.+?)`/g, '<code>$1</code>')
            .replace(/```(\w+)?\n([\s\S]+?)```/g, '<pre><code class="language-$1">$2</code></pre>')
            .replace(/!\[(.+?)\]\((.+?)\)/g, (match, alt, src) => {
                return `<img src="${sanitizeUrl(src)}" alt="${escapeHtml(alt)}" loading="lazy" style="max-width:100%; height:auto; display:block; margin: 10px 0; border-radius: 8px;">`;
            })
            .replace(/\[(.+?)\]\((.+?)\)/g, (match, text, href) => {
                return `<a href="${sanitizeUrl(href)}" target="_blank" rel="noopener noreferrer">${text}</a>`;
            })
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

    function isAuthenticated() {
        return sessionStorage.getItem(AUTH_KEY) === 'true' && !!sessionStorage.getItem(TOKEN_KEY);
    }

    function clearSession() {
        sessionStorage.removeItem(AUTH_KEY);
        sessionStorage.removeItem(TOKEN_KEY);
    }

    /**
     * 统一 API 请求
     * - 自动携带 X-Auth-Token
     * - 收到 401 时自动清除会话并返回 response（调用方决定如何引导重新验证）
     */
    function apiFetch(apiBaseUrl, url, options = {}) {
        const opts = Object.assign({}, options);
        const headers = Object.assign({
            'X-Auth-Token': sessionStorage.getItem(TOKEN_KEY) || ''
        }, opts.headers || {});
        opts.headers = headers;

        return fetch(`${apiBaseUrl}${url}`, opts).then((response) => {
            if (response.status === 401) {
                clearSession();
            }
            return response;
        });
    }

    /**
     * 统一密码验证：调用 /api/verify-password，成功后保存会话令牌
     * @returns {Promise<boolean>}
     */
    function verifyPassword(apiBaseUrl, password) {
        return fetch(`${apiBaseUrl}/api/verify-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success === true) {
                    sessionStorage.setItem(AUTH_KEY, 'true');
                    sessionStorage.setItem(TOKEN_KEY, password);
                    return true;
                }
                return false;
            })
            .catch((error) => {
                console.error('密码验证错误:', error);
                return false;
            });
    }

    /**
     * 统一的密码验证对话框
     * @param {Object} options
     * @param {string} options.apiBaseUrl API 地址
     * @param {string} options.action 操作描述（如"发布文章"）
     * @param {Function} options.onSuccess 验证成功回调
     * @param {string} [options.title='🔐 密码验证'] 对话框标题
     * @param {'modal'|'login'} [options.variant='modal'] 弹窗样式（login 用于整页登录）
     * @param {string} [options.backLinkHtml=''] 登录变体底部的返回链接 HTML
     */
    function showPasswordDialog(options) {
        const {
            apiBaseUrl,
            action,
            onSuccess,
            title = '🔐 密码验证',
            variant = 'modal',
            backLinkHtml = ''
        } = options || {};

        // 移除已存在的对话框
        const existing = document.getElementById('passwordDialog');
        if (existing) existing.remove();

        const dialog = document.createElement('div');
        dialog.id = 'passwordDialog';

        if (variant === 'login') {
            dialog.className = 'login-overlay';
            dialog.innerHTML = `
                <div class="login-box">
                    <h2>${title}</h2>
                    <p>请输入管理密码</p>
                    <input type="password" id="passwordInput" class="form-input" placeholder="输入密码" autocomplete="off">
                    <p id="passwordError" class="error-text" style="display: none;"></p>
                    <button id="confirmPasswordBtn" class="btn btn-primary">登录</button>
                    ${backLinkHtml}
                </div>
            `;
        } else {
            dialog.className = 'modal';
            dialog.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>${title}</h3>
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
        }
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

            const isValid = await verifyPassword(apiBaseUrl, password);
            if (isValid) {
                closeDialog();
                if (typeof onSuccess === 'function') onSuccess();
            } else {
                passwordError.textContent = '密码错误，请重试';
                passwordError.style.display = 'block';
                confirmBtn.disabled = false;
                confirmBtn.textContent = variant === 'login' ? '登录' : '确认';
                passwordInput.value = '';
                passwordInput.focus();
            }
        };

        confirmBtn.addEventListener('click', handleConfirm);
        if (cancelBtn) cancelBtn.addEventListener('click', closeDialog);
        if (closeBtn) closeBtn.addEventListener('click', closeDialog);
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog) closeDialog();
        });
        passwordInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') handleConfirm();
            if (e.key === 'Escape') closeDialog();
        });
    }

    global.BlogApp = {
        escapeHtml: escapeHtml,
        sanitizeUrl: sanitizeUrl,
        markdownToHtml: markdownToHtml,
        isAuthenticated: isAuthenticated,
        clearSession: clearSession,
        apiFetch: apiFetch,
        verifyPassword: verifyPassword,
        showPasswordDialog: showPasswordDialog,
        TOKEN_KEY: TOKEN_KEY,
        AUTH_KEY: AUTH_KEY
    };
})(typeof window !== 'undefined' ? window : globalThis);
