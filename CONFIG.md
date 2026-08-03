# Hugo博客发布器配置说明

## 环境变量配置

### 1. 后端环境变量 (Railway/Render/Vercel)

在后端服务平台（如Railway、Render、Vercel）设置以下环境变量：

```env
# 基础配置
PORT=5000
DEBUG=false
FRONTEND_URL=https://your-project.pages.dev   # CORS白名单，* 表示允许所有
PUBLISH_PASSWORD=your-publish-password        # 发布密码

# DeepSeek API配置
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash

# GitHub配置
GITHUB_TOKEN=ghp-your-github-personal-access-token
GITHUB_USERNAME=your-github-username
GITHUB_REPO=hugo-blog

# NVIDIA 多模态 API 配置（可选，用于小红书图片OCR）
NVIDIA_API_KEY=your-nvidia-api-key
NVIDIA_MODEL=stepfun-ai/step-3.7-flash

# QStash 异步任务配置（可选，不配置则回退同步发布）
QSTASH_TOKEN=your-qstash-token
QSTASH_CURRENT_SIGNING_KEY=your-qstash-current-signing-key
QSTASH_NEXT_SIGNING_KEY=your-qstash-next-signing-key

# Upstash Redis 配置（可选，用于持久化任务历史）
UPSTASH_REDIS_REST_URL=your-upstash-redis-url
UPSTASH_REDIS_REST_TOKEN=your-upstash-redis-token

# Webhook 基础地址（QStash 回调地址，部署后必填）
WEBHOOK_BASE_URL=https://your-api.example.com

# apihz.cn 第三方解析 API 凭证（小红书/今日头条抓取，必填）
APIHZ_DEVELOPER_ID=your-apihz-developer-id
APIHZ_API_KEY=your-apihz-api-key
```

> 完整变量清单见 `.env.example`，所有变量均可选（除 DeepSeek/GitHub 外），缺省时功能自动降级。

### 2. GitHub Token获取方法

1. 访问 GitHub Settings → Developer settings → Personal access tokens
2. 点击 "Generate new token (classic)"
3. 设置token名称，选择权限：
   - ✅ repo (完整控制私有仓库)
   - ✅ workflow
4. 生成token并保存

### 3. 前端配置 (frontend/config.js)

```javascript
const CONFIG = {
    // 后端API地址（部署后修改）
    API_BASE_URL: 'https://your-backend-api.railway.app',
    
    // 默认配置
    DEFAULT_TARGET_DIR: 'content/posts',  // Hugo文章目录
    DEFAULT_LAYOUT: 'post',                // 默认布局
    DEFAULT_LANGUAGE_CODE: 'zh-CN',        // 默认语言
};
```

## 部署步骤

### 后端部署 (Railway)

1. 登录 Railway 网站
2. 点击 "New Project" → "Deploy from GitHub"
3. 选择本仓库
4. 在Variables中添加上述环境变量
5. 启动命令由 `Procfile` 指定：`gunicorn app:app --bind 0.0.0.0:$PORT`（Railway 会挂载 `backend` 目录为工作目录）
6. 部署完成后获取API地址

> 也可以在 Vercel 部署（见 `VERCEL_DEPLOY.md`），入口为 `api/index.py`。

### 前端部署 (Cloudflare Pages)

1. 登录 Cloudflare Dashboard
2. 进入 "Pages" → "Connect to Git"
3. 选择本仓库的frontend目录
4. 构建命令留空
5. 输出目录：`frontend`
6. 部署完成后获取访问地址

### 更新前端配置

部署完成后，修改 `frontend/config.js` 中的 `API_BASE_URL` 为实际的后端地址。

## 目录结构说明

```
content/
├── posts/              # 博客文章目录
│   └── 2024/          # 按年份分类
│       └── 12-article-title.md
├── about.md           # 关于页面
└── ...
```

发布器会按照Hugo标准格式生成文件头：

```yaml
---
title: "文章标题"
date: 2024-12-25T10:30:00+08:00
draft: false
tags: ["标签1", "标签2"]
categories: ["分类1"]
---
```

## 常见问题

### Q: 发布后博客没有更新？
A: 确保GitHub Actions自动部署正常工作，检查仓库的Actions标签页。

### Q: DeepSeek排版失败？
A: 检查API密钥是否正确，确认API余额充足。

### Q: GitHub上传失败？
A: 检查Token权限，确认目标目录存在。

## 联系支持

如有问题，请在GitHub仓库中创建Issue。
