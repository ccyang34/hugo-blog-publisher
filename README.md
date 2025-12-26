# Hugo Blog Publisher

一个功能完整的Web版Hugo博客发布器，支持使用DeepSeek AI优化文章排版，并一键发布到GitHub。

## 功能特性

- **AI文章优化**：使用DeepSeek API自动优化文章排版、修正错别字、优化段落结构
- **Hugo格式支持**：自动生成符合Hugo要求的Markdown格式和front matter
- **一键发布**：直接将文章发布到GitHub仓库的指定目录
- **实时预览**：支持预览格式化后的文章效果
- **标签管理**：支持设置分类和标签
- **草稿功能**：可以选择将文章发布为草稿

## 项目结构

```
hugo-blog-publisher/
├── frontend/                 # 前端 (部署到Cloudflare Pages)
│   ├── index.html           # 主页面
│   ├── style.css            # 样式文件
│   ├── app.js               # 前端逻辑
│   └── config.js            # 前端配置
│
├── backend/                  # 后端API (部署到Railway/Render)
│   ├── app.py               # Flask主程序
│   ├── requirements.txt     # Python依赖
│   ├── services/            # 服务层
│   │   ├── deepseek.py     # DeepSeek API服务
│   │   └── github.py       # GitHub上传服务
│   └── utils/               # 工具函数
│       └── markdown.py      # Markdown格式处理
│
├── railway.json             # Railway部署配置
├── Procfile                 # Gunicorn启动配置
└── CONFIG.md               # 环境变量配置说明
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/hugo-blog-publisher.git
cd hugo-blog-publisher
```

### 2. 配置环境变量

创建 `.env` 文件（后端）：

```env
# DeepSeek API配置
DEEPSEEK_API_KEY=sk-your-deepseek-api-key

# GitHub配置
GITHUB_TOKEN=ghp-your-github-personal-access-token
GITHUB_USERNAME=your-github-username
GITHUB_REPO=hugo-blog  # 你的Hugo博客仓库名

# 安全配置
SECRET_KEY=your-random-secret-key

# CORS配置（前端地址）
FRONTEND_URL=https://your-project.pages.dev
```

更新 `frontend/config.js` 中的后端API地址：

```javascript
const API_BASE_URL = 'https://your-backend-service.railway.app';
```

### 3. 本地运行后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

后端服务将在 `http://localhost:5000` 启动。

### 4. 本地运行前端

使用任意静态文件服务器，例如：

```bash
# 使用Python
cd frontend
python -m http.server 8080

# 或使用Node.js
npx serve frontend
```

前端将在 `http://localhost:8080` 打开。

## 部署

### 部署后端到Railway

1. 在 [Railway](https://railway.app) 注册账号并创建新项目
2. 连接你的GitHub仓库
3. 设置环境变量（参考上面的 `.env` 文件）
4. 部署完成后，Railway会提供一个URL，例如：`https://your-app.railway.app`

### 部署前端到Cloudflare Pages

1. 在Cloudflare Dashboard中进入Pages页面
2. 连接你的GitHub仓库
3. 设置构建设置：
   - 构建命令：（留空）
   - 输出目录：`frontend`
4. 设置环境变量：（如果需要）
5. 点击"部署站点"

部署完成后，Cloudflare会提供一个URL，例如：`https://your-project.pages.dev`

### 更新前端配置

部署完成后，更新 `frontend/config.js` 中的 `API_BASE_URL` 为你的后端API地址，然后重新部署前端。

## API文档

### 健康检查

```
GET /api/health
```

响应：
```json
{
    "status": "ok",
    "timestamp": "2024-12-25T10:30:00"
}
```

### 文章格式化

```
POST /api/format
Content-Type: application/json

{
    "content": "原始文章内容",
    "title": "文章标题（可选）",
    "tags": ["标签1", "标签2"]（可选）,
    "category": "分类"（可选）
}
```

### 预览生成

```
POST /api/preview
Content-Type: application/json

{
    "title": "文章标题",
    "content": "文章内容",
    "date": "2024-12-25"（可选）,
    "tags": ["标签1", "标签2"]（可选）,
    "category": "分类"（可选）
}
```

### 发布文章

```
POST /api/publish
Content-Type: application/json

{
    "title": "文章标题",
    "content": "文章内容（Markdown格式）",
    "date": "2024-12-25"（可选）,
    "tags": ["标签1", "标签2"]（可选）,
    "category": "分类"（可选）,
    "target_dir": "content/posts"（可选）,
    "draft": false（可选）
}
```

## 使用说明

1. 在前端页面输入文章标题、内容、选择分类和标签
2. 点击"DeepSeek优化排版"按钮，AI会自动优化文章格式
3. 点击"预览"按钮查看格式化后的效果
4. 选择发布目录（文章/笔记/草稿）
5. 点击"发布到GitHub"按钮，文章将自动上传到你的Hugo博客仓库

## GitHub Token权限要求

创建GitHub Personal Access Token时，需要以下权限：
- `repo` - 完整仓库访问权限（用于上传文件）
- 或仅 `public_repo` - 如果仓库是公开的

## 注意事项

- 确保GitHub Token有足够的权限访问你的博客仓库
- DeepSeek API调用会产生一定的费用，请注意使用频率
- 建议定期检查和更新API密钥
- 发布前建议先预览确认文章格式正确

## 技术栈

**前端：**
- 原生HTML/CSS/JavaScript
- 响应式设计，支持深色模式
- Cloudflare Pages托管

**后端：**
- Python Flask
- DeepSeek API
- GitHub API
- Railway/Render部署

## 许可证

MIT License
