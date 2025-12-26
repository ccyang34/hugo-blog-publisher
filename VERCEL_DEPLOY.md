# 在 Vercel 部署后端教程

本教程将指导您如何在 Vercel 上部署 Hugo 博客发布器的后端 API。

## 准备工作

在开始之前，请确保您已经准备好：

1. **Vercel 账号** - 注册地址：https://vercel.com（免费）
2. **GitHub 账号** - 已有的
3. **项目代码已推送到 GitHub**
4. **DeepSeek API Key** - 获取地址：https://platform.deepseek.com
5. **GitHub Personal Access Token** - 用于访问您的博客仓库

---

## 第一步：获取 GitHub Personal Access Token

这个 Token 用于让发布器访问您的 GitHub 博客仓库并上传文件。

### 获取 Token 的步骤：

1. 打开 GitHub，点击右上角头像 → **Settings**

2. 左侧菜单向下滚动，点击 **Developer settings**

3. 点击 **Personal access tokens** → **Tokens (classic)**

4. 点击 **Generate new token (classic)**

5. 设置 Token 名称（建议：`hugo-publisher-token`）

6. 设置过期时间，建议选择 **No expiration**（永不过期）

7. 勾选以下权限：
   - ☑️ `repo` - 完整控制私有仓库（必须勾选）

8. 点击页面底部的 **Generate token**

9. **重要**：复制生成的 Token，它只显示一次，保存好

Token 格式类似：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## 第二步：将项目推送到 GitHub

如果项目还没有推送到 GitHub，请按以下步骤操作：

### 2.1 创建 GitHub 仓库

1. 打开 https://github.com/new

2. 仓库名称：`hugo-blog-publisher`（可以自定义）

3. 选择 **Private**（私有）或 **Public**（公开）

4. 不要勾选任何初始化选项

5. 点击 **Create repository**

### 2.2 本地初始化并推送

打开终端，进入项目目录：

```bash
cd /Users/ccy/hugo-blog-publisher

# 初始化 Git 仓库（如果还没有）
git init

# 添加所有文件
git add .

# 提交代码
git commit -m "Initial commit: Hugo blog publisher"

# 连接远程仓库（将 your-username 替换为您的 GitHub 用户名）
git remote add origin https://github.com/your-username/hugo-blog-publisher.git

# 推送到 GitHub
git branch -M main
git push -u origin main
```

---

## 第三步：在 Vercel 创建项目

### 3.1 登录 Vercel

1. 打开 https://vercel.com 并登录

2. 如果没有账号，可以使用 GitHub 账号注册（推荐）

### 3.2 创建新项目

1. 登录后，点击右上角的 **Add New...** 按钮

2. 选择 **Project**

3. Vercel 会显示您的 GitHub 仓库列表

4. 找到并选择 `hugo-blog-publisher` 仓库

5. 点击 **Import**

### 3.3 配置项目

在项目配置页面，填写以下信息：

| 配置项 | 值 |
|--------|-----|
| **Project Name** | `hugo-blog-publisher`（可以自定义） |
| **Framework Preset** | **Other** |
| **Root Directory** | `./`（保持默认） |
| **Build Command** | （留空） |
| **Output Directory** | （留空） |

**重要**：确保 **Framework Preset** 选择为 **Other**，因为这是一个 Python Flask 项目。

---

## 第四步：配置环境变量

环境变量是配置后端的关键步骤，必须正确设置。

### 4.1 添加环境变量

在项目配置页面的 **Environment Variables** 部分，点击 **Add New** 按钮，逐个添加以下变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `DEEPSEEK_API_KEY` | `sk-xxxxx` | 您的 DeepSeek API Key |
| `GITHUB_TOKEN` | `ghp_xxxxx` | 第一步获取的 GitHub Token |
| `GITHUB_USERNAME` | `your-username` | 您的 GitHub 用户名 |
| `GITHUB_REPO` | `hugo-blog` | 您的 Hugo 博客仓库名 |
| `SECRET_KEY` | `任意随机字符串` | 用于加密，建议 32 位以上 |
| `FRONTEND_URL` | `*` | 允许的前端地址，`*` 表示允许所有 |
| `DEBUG` | `false` | 生产环境设为 false |

### 4.2 环境变量说明

- **DEEPSEEK_API_KEY**: 从 https://platform.deepseek.com 获取
- **GITHUB_TOKEN**: 第一步获取的 GitHub Personal Access Token
- **GITHUB_USERNAME**: 您的 GitHub 用户名（不是邮箱）
- **GITHUB_REPO**: 您的 Hugo 博客仓库名称（例如：`hugo-blog`）
- **SECRET_KEY**: 任意随机字符串，例如：`my-secret-key-1234567890abcdef`
- **FRONTEND_URL**: 前端地址，暂时设为 `*` 允许所有来源，部署前端后可以更新为具体地址
- **DEBUG**: 生产环境设为 `false`

### 4.3 选择环境

在添加环境变量时，可以选择：
- **Production**: 生产环境（部署到主域名）
- **Preview**: 预览环境（每次 PR 都会部署）

建议先选择 **Production**，这样所有环境都会使用这些变量。

---

## 第五步：部署项目

### 5.1 开始部署

1. 确认所有配置都正确

2. 点击页面底部的 **Deploy** 按钮

3. Vercel 会开始构建和部署您的项目

### 5.2 等待部署完成

部署过程通常需要 1-3 分钟，您可以看到：

- **Building** - 正在构建
- **Installing dependencies** - 正在安装 Python 依赖
- **Deploying** - 正在部署

部署成功后，页面会显示：

```
✓ Production: https://hugo-blog-publisher.vercel.app
```

**保存好这个地址**，后面配置前端需要用到。

---

## 第六步：验证部署

### 6.1 测试健康检查接口

在浏览器中打开：
```
https://您的项目名.vercel.app/api/health
```

如果返回类似以下内容，说明部署成功：
```json
{
  "status": "ok",
  "timestamp": "2024-12-26T10:30:00.123456"
}
```

### 6.2 测试其他接口

您也可以测试其他接口：

- **配置接口**:
  ```
  https://您的项目名.vercel.app/api/config
  ```

- **密码验证接口**（使用 POST 请求）:
  ```
  POST https://您的项目名.vercel.app/api/verify-password
  Body: {"password": "您的密码"}
  ```

---

## 第七步：更新前端配置

现在需要将前端配置中的后端 API 地址更新为 Vercel 的实际地址。

### 7.1 编辑 frontend/config.js

打开 [frontend/config.js](file:///Users/ccy/hugo-blog-publisher/frontend/config.js)，更新 API 地址：

```javascript
// 将这一行更新为您的 Vercel 后端地址
const API_BASE_URL = 'https://您的项目名.vercel.app';
```

例如：
```javascript
const API_BASE_URL = 'https://hugo-blog-publisher.vercel.app';
```

### 7.2 推送更新到 GitHub

```bash
git add frontend/config.js
git commit -m "Update API base URL for Vercel deployment"
git push
```

---

## 第八步：更新后端 CORS 配置（可选）

如果您想限制只有特定前端可以访问后端，可以更新 CORS 配置。

### 8.1 更新环境变量

1. 打开 Vercel 项目页面

2. 点击顶部的 **Settings** 标签

3. 左侧菜单点击 **Environment Variables**

4. 找到 `FRONTEND_URL`，将值更新为您的 Cloudflare 前端地址：
   ```
   https://hugo-blog-publisher.pages.dev
   ```

5. 点击 **Save**

6. Vercel 会自动重新部署

---

## 常见问题排查

### 问题 1：部署失败 - "Build failed"

**可能原因**：
- Python 版本不兼容
- 依赖安装失败

**解决方法**：
1. 在 Vercel 项目页面，点击 **Deployments** 标签
2. 点击失败的部署，查看详细日志
3. 检查 [backend/requirements.txt](file:///Users/ccy/hugo-blog-publisher/backend/requirements.txt) 中的依赖版本
4. 确认 [vercel.json](file:///Users/ccy/hugo-blog-publisher/vercel.json) 配置正确

### 问题 2：API 返回 500 错误

**可能原因**：
- 环境变量未设置或设置错误
- DeepSeek API Key 无效
- GitHub Token 权限不足

**解决方法**：
1. 在 Vercel 项目页面，点击 **Settings** → **Environment Variables**
2. 确认所有环境变量都已正确设置
3. 查看 Vercel 的函数日志获取详细错误信息

### 问题 3：CORS 跨域错误

**可能原因**：
- 前端地址没有添加到后端的 `FRONTEND_URL`

**解决方法**：
1. 将 `FRONTEND_URL` 设置为 `*` 允许所有来源
2. 或者设置为具体的前端地址

### 问题 4：DeepSeek 排版失败

**可能原因**：
- API Key 无效
- API 余额不足
- 网络问题

**解决方法**：
1. 确认 `DEEPSEEK_API_KEY` 环境变量正确
2. 检查 DeepSeek 账户余额
3. 查看 Vercel 函数日志中的具体错误信息

### 问题 5：GitHub 上传失败

**可能原因**：
- Token 权限不足
- 仓库名称错误
- 目标目录不存在

**解决方法**：
1. 确认 Token 有 `repo` 权限
2. 确认 `GITHUB_REPO` 是正确的仓库名
3. 确认目标目录（如 `content/posts`）在仓库中存在

---

## 查看 Vercel 日志

### 查看部署日志

1. 打开 Vercel 项目页面

2. 点击 **Deployments** 标签

3. 点击任意一次部署，可以看到：
   - 构建日志
   - 部署日志
   - 错误信息

### 查看函数日志

1. 打开 Vercel 项目页面

2. 点击 **Functions** 标签

3. 可以看到所有 API 调用的日志，包括：
   - 请求时间
   - 响应状态
   - 错误信息

---

## 后续维护

### 更新代码

1. 本地修改代码

2. 推送到 GitHub：
   ```bash
   git add .
   git commit -m "描述您的更改"
   git push
   ```

3. Vercel 会自动检测到更新并重新部署

### 手动重新部署

如果需要手动触发重新部署：

1. 打开 Vercel 项目页面

2. 点击 **Deployments** 标签

3. 点击右上角的 **...** 菜单

4. 选择 **Redeploy**

### 查看部署历史

1. 打开 Vercel 项目页面

2. 点击 **Deployments** 标签

3. 可以看到所有的部署历史记录

---

## Vercel 项目结构

```
hugo-blog-publisher/
├── api/                    # Vercel 函数目录
│   └── index.py           # Vercel 入口文件
├── backend/               # 后端代码
│   ├── app.py            # Flask 应用
│   ├── requirements.txt  # Python 依赖
│   ├── services/         # 服务层
│   └── utils/            # 工具类
├── frontend/             # 前端代码
├── vercel.json           # Vercel 配置文件
└── README.md
```

---

## Vercel 免费额度

Vercel 的免费套餐包括：

- ✅ 无限项目
- ✅ 100GB 带宽/月
- ✅ 100GB-Hours 计算时间/月
- ✅ 自动 HTTPS
- ✅ 全球 CDN
- ✅ 自动部署

对于这个博客发布器项目，免费额度完全够用。

---

## 部署架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户浏览器                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Cloudflare Pages (前端)                         │
│          https://hugo-blog-publisher.pages.dev              │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS 请求
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               Vercel (后端 API)                              │
│        https://hugo-blog-publisher.vercel.app               │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐     │
│  │ DeepSeek    │  │  GitHub     │  │  图片上传       │     │
│  │ Service     │  │  Service    │  │  /api/upload-   │     │
│  │ /api/format │  │  /api/publish│  │  image          │     │
│  └─────────────┘  └─────────────┘  └─────────────────┘     │
└─────────────────────────┬───────────────────────────────────┘
                          │ GitHub API
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    GitHub 仓库                               │
│          hugo-blog (您的 Hugo 博客仓库)                      │
│                                                              │
│  ├── content/posts/    ← 文章发布到这里                      │
│  ├── content/notes/    ← 笔记发布到这里                      │
│  └── static/images/    ← 图片上传到这里                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 总结

通过以上步骤，您已经成功在 Vercel 上部署了后端 API。现在您可以：

1. ✅ 使用 DeepSeek AI 优化文章排版
2. ✅ 将文章发布到 GitHub 仓库
3. ✅ 上传图片到 GitHub
4. ✅ 管理博客文件

如果遇到问题，请查看 **常见问题排查** 部分或查看 Vercel 日志。

祝您使用愉快！🎉
