const API_BASE = '';

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

function copyToClipboard(elementId) {
    const textarea = document.getElementById(elementId);
    textarea.select();
    document.execCommand('copy');
    showToast('已复制到剪贴板', 'success');
}

function showResult(resultId, content, type = 'success') {
    const result = document.getElementById(resultId);
    result.classList.remove('hidden', 'success', 'error');
    result.classList.add(type);
    result.innerHTML = content;
}

function hideResult(resultId) {
    const result = document.getElementById(resultId);
    result.classList.add('hidden');
}

async function formatArticle() {
    const title = document.getElementById('format-title').value;
    const tags = document.getElementById('format-tags').value.split(',').map(t => t.trim()).filter(t => t);
    const category = document.getElementById('format-category').value;
    const content = document.getElementById('format-content').value;

    if (!content.trim()) {
        showToast('请输入文章内容', 'error');
        return;
    }

    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> 处理中...';

    try {
        const response = await fetch(`${API_BASE}/api/format`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title,
                tags,
                category,
                content
            })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('format-output').value = data.formatted_content;
            document.getElementById('format-result').classList.remove('hidden');
            showToast('排版完成', 'success');
        } else {
            showToast(data.error || '排版失败', 'error');
        }
    } catch (error) {
        showToast('请求失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🤖 DeepSeek 优化排版';
    }
}

async function previewArticle() {
    const title = document.getElementById('preview-title').value;
    const date = document.getElementById('preview-date').value;
    const tags = document.getElementById('preview-tags').value.split(',').map(t => t.trim()).filter(t => t);
    const category = document.getElementById('preview-category').value;
    const content = document.getElementById('preview-content').value;

    if (!title.trim()) {
        showToast('请输入文章标题', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/preview`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title,
                date,
                tags,
                category,
                content
            })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('preview-output').value = data.front_matter;
            document.getElementById('preview-result').classList.remove('hidden');
            showToast('预览生成成功', 'success');
        } else {
            showToast(data.error || '生成预览失败', 'error');
        }
    } catch (error) {
        showToast('请求失败: ' + error.message, 'error');
    }
}

async function publishArticle() {
    const title = document.getElementById('publish-title').value;
    const date = document.getElementById('publish-date').value;
    const tags = document.getElementById('publish-tags').value.split(',').map(t => t.trim()).filter(t => t);
    const category = document.getElementById('publish-category').value;
    const targetDir = document.getElementById('publish-target-dir').value;
    const content = document.getElementById('publish-content').value;
    const password = document.getElementById('publish-password').value;

    if (!title.trim() || !content.trim()) {
        showToast('请填写标题和内容', 'error');
        return;
    }

    if (!password.trim()) {
        showToast('请输入发布密码', 'error');
        return;
    }

    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> 发布中...';

    try {
        const verifyResponse = await fetch(`${API_BASE}/api/verify-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ password })
        });

        const verifyData = await verifyResponse.json();

        if (!verifyData.success) {
            showToast('密码错误', 'error');
            btn.disabled = false;
            btn.innerHTML = '🚀 发布到 GitHub';
            return;
        }

        const publishResponse = await fetch(`${API_BASE}/api/publish`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title,
                date,
                tags,
                category,
                target_dir: targetDir,
                content
            })
        });

        const publishData = await publishResponse.json();

        if (publishData.success) {
            showResult('publish-result', `
                <h3>✅ 发布成功！</h3>
                <p><strong>文件路径：</strong>${publishData.file_path}</p>
                <p><strong>GitHub URL：</strong><a href="${publishData.url}" target="_blank">${publishData.url}</a></p>
            `, 'success');
            showToast('文章发布成功', 'success');
        } else {
            showResult('publish-result', `
                <h3>❌ 发布失败</h3>
                <p>${publishData.error}</p>
            `, 'error');
            showToast('发布失败', 'error');
        }
    } catch (error) {
        showResult('publish-result', `
            <h3>❌ 请求失败</h3>
            <p>${error.message}</p>
        `, 'error');
        showToast('请求失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🚀 发布到 GitHub';
    }
}

async function uploadImage() {
    const fileInput = document.getElementById('upload-file');
    const customName = document.getElementById('upload-custom-name').value;
    const password = document.getElementById('upload-password').value;

    if (!fileInput.files[0]) {
        showToast('请选择图片文件', 'error');
        return;
    }

    if (!password.trim()) {
        showToast('请输入发布密码', 'error');
        return;
    }

    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> 上传中...';

    try {
        const verifyResponse = await fetch(`${API_BASE}/api/verify-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ password })
        });

        const verifyData = await verifyResponse.json();

        if (!verifyData.success) {
            showToast('密码错误', 'error');
            btn.disabled = false;
            btn.innerHTML = '📤 上传图片';
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        if (customName.trim()) {
            formData.append('custom_name', customName);
        }

        const uploadResponse = await fetch(`${API_BASE}/api/upload-image`, {
            method: 'POST',
            body: formData
        });

        const uploadData = await uploadResponse.json();

        if (uploadData.success) {
            showResult('upload-result', `
                <h3>✅ 上传成功！</h3>
                <p><strong>文件名：</strong>${uploadData.filename}</p>
                <p><strong>图片 URL：</strong><code>${uploadData.url}</code></p>
                <p><strong>Markdown 引用：</strong><code>![${uploadData.filename}](${uploadData.url})</code></p>
            `, 'success');

            // 自动插入到内容框
            insertImageToContent(uploadData.url, uploadData.filename);

            showToast('图片上传成功', 'success');
        } else {
            showResult('upload-result', `
                <h3>❌ 上传失败</h3>
                <p>${uploadData.error}</p>
            `, 'error');
            showToast('上传失败', 'error');
        }
    } catch (error) {
        showResult('upload-result', `
            <h3>❌ 请求失败</h3>
            <p>${error.message}</p>
        `, 'error');
        showToast('请求失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '📤 上传图片';
    }
}

function insertImageToContent(url, filename) {
    const textarea = document.getElementById('format-content');
    if (!textarea) return;

    const imageMarkdown = `![${filename}](${url})`;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;

    // 如果没有内容，直接添加；如果有内容，确保换行
    let prefix = '';
    if (text.length > 0 && start > 0 && text[start - 1] !== '\n') {
        prefix = '\n';
    }

    const newText = text.substring(0, start) + prefix + imageMarkdown + text.substring(end);
    textarea.value = newText;

    const newCursorPos = start + prefix.length + imageMarkdown.length;
    textarea.selectionStart = textarea.selectionEnd = newCursorPos;
    textarea.focus();
}

async function listFiles() {
    const path = document.getElementById('files-path').value;

    try {
        const response = await fetch(`${API_BASE}/api/files?path=${encodeURIComponent(path)}`);
        const data = await response.json();

        if (data.success) {
            const filesList = document.getElementById('files-list');

            if (data.files.length === 0) {
                filesList.innerHTML = '<p style="color: #666; padding: 20px;">暂无文件</p>';
            } else {
                filesList.innerHTML = data.files.map(file => `
                    <div class="file-item">
                        <span class="file-name">📄 ${file.name}</span>
                        <div class="file-actions">
                            <button onclick="viewFile('${file.path}')" class="btn btn-secondary">查看</button>
                            <button onclick="deleteFile('${file.path}')" class="btn btn-danger">删除</button>
                        </div>
                    </div>
                `).join('');
            }

            document.getElementById('files-result').classList.remove('hidden');
            showToast(`找到 ${data.files.length} 个文件`, 'success');
        } else {
            showToast(data.error || '获取文件列表失败', 'error');
        }
    } catch (error) {
        showToast('请求失败: ' + error.message, 'error');
    }
}

async function viewFile(path) {
    try {
        const response = await fetch(`${API_BASE}/api/file?path=${encodeURIComponent(path)}`);
        const data = await response.json();

        if (data.success) {
            const newWindow = window.open('', '_blank');
            newWindow.document.write(`
                <html>
                <head><title>${path}</title></head>
                <body style="font-family: monospace; padding: 20px; white-space: pre-wrap;">${data.content}</body>
                </html>
            `);
        } else {
            showToast(data.error || '获取文件内容失败', 'error');
        }
    } catch (error) {
        showToast('请求失败: ' + error.message, 'error');
    }
}

async function deleteFile(path) {
    if (!confirm(`确定要删除文件 "${path}" 吗？`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/file?path=${encodeURIComponent(path)}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
            showToast('文件删除成功', 'success');
            listFiles();
        } else {
            showToast(data.error || '删除文件失败', 'error');
        }
    } catch (error) {
        showToast('请求失败: ' + error.message, 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;

            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });

    document.getElementById('preview-date').valueAsDate = new Date();
    document.getElementById('publish-date').valueAsDate = new Date();
});
