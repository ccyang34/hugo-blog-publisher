# Hugo 博客 + 发布器完整部署教程

> 本教程将手把手教你从零开始部署一个完整的博客系统，包括 Hugo 博客本体和文章发布后台。即使你是小白，按照步骤操作也能成功！

---

## 📋 目录

1. [整体架构介绍](#整体架构介绍)
2. [准备工作](#准备工作)
3. [第一部分：部署 Hugo 博客到 Cloudflare Pages](#第一部分部署-hugo-博客到-cloudflare-pages)
4. [第二部分：部署发布器后端 API 到 Vercel](#第二部分部署发布器后端-api-到-vercel)
5. [第三部分：部署发布器前端到 Cloudflare Pages](#第三部分部署发布器前端到-cloudflare-pages)
6. [第四部分：自定义域名配置](#第四部分自定义域名配置)
7. [常见问题排查](#常见问题排查)

---

## 整体架构介绍

整个系统由三个部分组成：

```
┌────────────────────────────────────────────────────────────────────┐
│                          用户                                       │
│                           │                                         │
│           ┌───────────────┼───────────────┐                        │
│           ▼               ▼               ▼                        │
│    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                │
│    │ Hugo 博客    │ │ 发布器前端   │ │ 发布器后端   │                │
│    │ Cloudflare  │ │ Cloudflare  │ │ Vercel      │                │
│    │ Pages       │ │ Pages       │ │             │                │
│    └─────────────┘ └──────┬──────┘ └──────┬──────┘                │
│                           │               │                        │
│                           │  API 请求     │                        │
│                           └───────────────┘                        │
│                                   │                                │
│                                   ▼                                │
│                          ┌─────────────┐                           │
│                          │ GitHub Repo │                           │
│                          │ (博客内容)   │                           │
│                          └─────────────┘                           │
└────────────────────────────────────────────────────────────────────┘
```

| 组件 | 托管平台 | 用途 |
|------|---------|------|
| Hugo 博客 | Cloudflare Pages | 展示博客内容 |
| 发布器前端 | Cloudflare Pages | 文章编辑界面 |
| 发布器后端 | Vercel | API 处理、AI 排版、GitHub 操作 |

---

## 准备工作

在开始之前，请准备好以下账号和工具：

### 🔧 必需的账号

| 账号 | 注册地址 | 用途 |
|------|---------|------|
| GitHub | https://github.com | 存储博客内容和代码 |
| Cloudflare | https://cloudflare.com | 托管前端页面 |
| Vercel | https://vercel.com | 托管后端 API |
| DeepSeek | https://platform.deepseek.com | AI 文章排版 |

### 🛠 需要安装的工具

**macOS 用户**：
```bash
# 安装 Homebrew（如果没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Hugo
brew install hugo

# 安装 Git
brew install git

# 安装 Node.js（可选，用于本地调试）
brew install node
```

**Windows 用户**：
1. 下载 Hugo: https://gohugo.io/installation/windows/
2. 下载 Git: https://git-scm.com/download/win
3. 下载 Node.js: https://nodejs.org/

### 🔑 需要获取的密钥

#### 1. GitHub Personal Access Token

1. 打开 GitHub → 右上角头像 → **Settings**
2. 左侧菜单向下滚动 → **Developer settings**
3. **Personal access tokens** → **Tokens (classic)**
4. **Generate new token (classic)**
5. 设置：
   - Note: `hugo-publisher`
   - Expiration: **No expiration**
   - 勾选: ☑️ **repo** (完整控制私有仓库)
6. 点击 **Generate token**
7. **立即复制保存** Token（只显示一次！）

格式：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### 2. DeepSeek API Key

1. 打开 https://platform.deepseek.com
2. 注册/登录账号
3. 进入 **API Keys** 页面
4. 点击 **Create new API key**
5. 复制保存 API Key

格式：`sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## 第一部分：部署 Hugo 博客到 Cloudflare Pages

### Step 1: 创建 Hugo 博客仓库

#### 方法一：使用现有的 Hugo 主题模板

1. 访问 https://github.com/new
2. 填写仓库信息：
   - Repository name: `hugo-blog`
   - 选择: **Private**（推荐）
3. 点击 **Create repository**

#### 方法二：Fork 一个现有的 Hugo 博客模板

推荐模板（Stack 主题）：
1. 访问 https://github.com/CaiJimmy/hugo-theme-stack-starter
2. 点击 **Use this template** → **Create a new repository**
3. 命名为 `hugo-blog`

### Step 2: 本地初始化博客

```bash
# 克隆仓库到本地
git clone https://github.com/你的用户名/hugo-blog.git
cd hugo-blog

# 如果是空仓库，初始化 Hugo
hugo new site . --force

# 添加主题（以 Stack 主题为例）
git submodule add https://github.com/CaiJimmy/hugo-theme-stack.git themes/hugo-theme-stack

# 复制主题的示例配置
cp -r themes/hugo-theme-stack/exampleSite/config.yaml ./config.yaml
```

### Step 3: 配置 Hugo

编辑 `config.yaml` 或 `hugo.toml`：

```yaml
baseURL: "https://你的域名.pages.dev"
languageCode: "zh-cn"
title: "我的博客"
theme: "hugo-theme-stack"

# 重要：设置输出格式
outputs:
  home:
    - HTML
    - RSS
    - JSON

# 启用 emoji
enableEmoji: true

# 分页
paginate: 10
```

### Step 4: 创建必要的目录结构

```bash
# 创建内容目录
mkdir -p content/posts
mkdir -p content/notes
mkdir -p static/images

# 创建一个测试文章
cat > content/posts/hello-world.md << 'EOF'
---
title: "Hello World"
date: 2025-01-01
draft: false
tags: ["测试"]
categories: ["默认"]
---

这是我的第一篇博客文章！
EOF
```

### Step 5: 推送到 GitHub

```bash
git add .
git commit -m "Initial Hugo blog setup"
git push origin main
```

### Step 6: 在 Cloudflare Pages 部署

1. 打开 https://dash.cloudflare.com
2. 左侧菜单 → **Workers & Pages** → **Create**
3. 选择 **Pages** → **Connect to Git**
4. 授权并选择 `hugo-blog` 仓库
5. 配置构建设置：

| 设置项 | 值 |
|-------|-----|
| Production branch | `main` |
| Framework preset | `Hugo` |
| Build command | `hugo --minify` |
| Build output directory | `public` |

6. 点击 **Environment variables** → 添加：
   - 变量名: `HUGO_VERSION`
   - 值: `0.140.0`

7. 点击 **Save and Deploy**

等待 1-2 分钟，部署成功后会显示：
```
✓ https://hugo-blog-xxx.pages.dev
```

---

## 第二部分：部署发布器后端 API 到 Vercel

### Step 1: 获取发布器代码

```bash
# 克隆发布器仓库
git clone https://github.com/你的用户名/hugo-blog-publisher.git
cd hugo-blog-publisher
```

或者如果你已经有代码，直接推送到 GitHub：

```bash
cd /你的发布器目录
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的用户名/hugo-blog-publisher.git
git branch -M main
git push -u origin main
```

### Step 2: 在 Vercel 创建项目

1. 打开 https://vercel.com 并登录（推荐用 GitHub 账号）
2. 点击 **Add New...** → **Project**
3. 选择 `hugo-blog-publisher` 仓库
4. 点击 **Import**

### Step 3: 配置 Vercel 项目

在项目配置页面：

| 配置项 | 值 |
|--------|-----|
| **Project Name** | `hugo-blog-publisher` |
| **Framework Preset** | **Other** |
| **Root Directory** | `./` |
| **Build Command** | （留空） |
| **Output Directory** | （留空） |

### Step 4: 配置环境变量（最重要！）

在 **Environment Variables** 部分，添加以下变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `DEEPSEEK_API_KEY` | `sk-xxxxx` | DeepSeek API Key |
| `GITHUB_TOKEN` | `ghp_xxxxx` | GitHub Token |
| `GITHUB_USERNAME` | `你的用户名` | GitHub 用户名 |
| `GITHUB_REPO` | `hugo-blog` | Hugo 博客仓库名 |
| `PUBLISH_PASSWORD` | `你的密码` | 发布密码（自定义） |
| `SECRET_KEY` | `随机32位字符串` | 加密密钥 |
| `FRONTEND_URL` | `*` | 允许的前端地址 |
| `DEBUG` | `false` | 调试模式 |

### Step 5: 部署

1. 点击 **Deploy** 按钮
2. 等待部署完成（约 1-3 分钟）
3. 部署成功后记录下 Vercel 分配的地址：
   ```
   https://hugo-blog-publisher-xxx.vercel.app
   ```

### Step 6: 验证部署

在浏览器打开：
```
https://你的项目名.vercel.app/api/health
```

如果返回：
```json
{"status": "ok", "timestamp": "..."}
```

说明后端部署成功！

---

## 第三部分：部署发布器前端到 Cloudflare Pages

### Step 1: 配置前端 API 地址

编辑 `frontend/config.js`：

```javascript
// 将 API 地址改为你的 Vercel 后端地址
const API_BASE_URL = 'https://hugo-blog-publisher-xxx.vercel.app';
```

### Step 2: 推送更新

```bash
git add frontend/config.js
git commit -m "Update API base URL"
git push
```

### Step 3: 在 Cloudflare Pages 部署前端

1. 打开 https://dash.cloudflare.com
2. **Workers & Pages** → **Create** → **Pages**
3. **Connect to Git** → 选择 `hugo-blog-publisher` 仓库
4. 配置构建设置：

| 设置项 | 值 |
|-------|-----|
| Production branch | `main` |
| Framework preset | `None` |
| Build command | （留空） |
| Build output directory | `frontend` |

5. 点击 **Save and Deploy**

部署成功后，记录地址：
```
https://hugo-blog-publisher-frontend.pages.dev
```

### Step 4: 更新后端 CORS 配置

回到 Vercel 项目设置：
1. **Settings** → **Environment Variables**
2. 修改 `FRONTEND_URL` 为：
   ```
   https://hugo-blog-publisher-frontend.pages.dev
   ```
3. 保存后 Vercel 会自动重新部署

---

## 第四部分：自定义域名配置

### 4.1 为 Hugo 博客配置自定义域名

#### 在 Cloudflare 配置

1. 打开 Cloudflare Dashboard → 你的域名
2. **DNS** → **Add record**
3. 添加 CNAME 记录：

| 类型 | 名称 | 内容 |
|------|------|------|
| CNAME | `blog` 或 `@` | `hugo-blog-xxx.pages.dev` |

4. 回到 **Workers & Pages** → 你的博客项目
5. **Custom domains** → **Set up a custom domain**
6. 输入你的域名：`blog.你的域名.com`
7. 点击 **Activate domain**

#### 更新 Hugo 配置

编辑 `config.yaml`：
```yaml
baseURL: "https://blog.你的域名.com"
```

推送更新：
```bash
git add config.yaml
git commit -m "Update base URL to custom domain"
git push
```

### 4.2 为发布器前端配置自定义域名

同样的步骤：

1. Cloudflare DNS 添加 CNAME：

| 类型 | 名称 | 内容 |
|------|------|------|
| CNAME | `publish` | `hugo-blog-publisher-frontend.pages.dev` |

2. 在 Cloudflare Pages 项目设置中添加自定义域名

### 4.3 为后端 API 配置自定义域名

1. 打开 Vercel 项目 → **Settings** → **Domains**
2. 点击 **Add**
3. 输入域名：`api.你的域名.com`
4. Vercel 会显示需要添加的 DNS 记录
5. 在 Cloudflare DNS 添加相应记录
6. 返回 Vercel 点击 **Verify**

---

## 常见问题排查

### ❌ 问题 1：Vercel 部署失败

**检查项**：
1. 确认 `vercel.json` 文件存在且格式正确
2. 确认 `requirements.txt` 中的依赖版本正确
3. 查看 Vercel 部署日志找具体错误

**vercel.json 正确格式**：
```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/api/index.py"
    }
  ]
}
```

### ❌ 问题 2：API 返回 500 错误

**检查项**：
1. 在 Vercel 项目 → **Functions** 查看日志
2. 确认所有环境变量都已正确设置
3. 确认 GitHub Token 有 `repo` 权限

### ❌ 问题 3：CORS 跨域错误

**解决方法**：
1. 确认 `FRONTEND_URL` 环境变量设置正确
2. 暂时设为 `*` 测试是否是 CORS 问题

### ❌ 问题 4：Hugo 博客页面 404

**检查项**：
1. 确认 `hugo.toml` 或 `config.yaml` 中的 `baseURL` 正确
2. 确认构建命令是 `hugo --minify`
3. 确认输出目录是 `public`

### ❌ 问题 5：图片无法显示

**检查项**：
1. 确认图片上传到 `static/images/` 目录
2. 在 Markdown 中使用正确的路径：`/images/xxx.jpg`

---

## 🎉 完成！

恭喜你！现在你拥有了一个完整的博客系统：

- 📝 **博客地址**：`https://blog.你的域名.com`
- ✍️ **发布器地址**：`https://publish.你的域名.com`
- 🔧 **API 地址**：`https://api.你的域名.com`

### 日常使用流程

1. 打开发布器页面
2. 输入发布密码
3. 粘贴文章内容或输入网址
4. 点击「优化并预览」
5. 确认无误后点击「快速发布」
6. 等待 1-2 分钟，博客自动更新

### 后续维护

- **更新代码**：本地修改后 `git push`，Vercel 和 Cloudflare 会自动重新部署
- **查看日志**：Vercel Dashboard → Functions → 查看 API 调用日志
- **监控流量**：Cloudflare Dashboard → Analytics

---

*教程最后更新：2026-01-04*
