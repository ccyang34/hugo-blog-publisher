# Hugo博客发布器配置说明

## 环境变量配置

### 1. 后端环境变量 (Railway/Render)

在后端服务平台（如Railway、Render）设置以下环境变量：

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
5. 设置启动命令：`gunicorn backend.app:app --bind 0.0.0.0:$PORT`
6. 部署完成后获取API地址

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
