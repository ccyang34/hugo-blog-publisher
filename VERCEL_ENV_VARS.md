# Vercel 后端环境变量配置说明

本文档汇总了在 Vercel 部署后端时所需要的关键环境变量及其说明，方便日后查询和修改。

## 环境变量列表

| 变量名 | 状态 | 适用环境 | 说明 |
| --- | --- | --- | --- |
| `QSTASH_TOKEN` | Needs Attention | All Environments | Upstash QStash 服务的鉴权 Token，用于执行定时任务或异步队列调用。 |
| `QSTASH_CURRENT_SIGNING_KEY` | Needs Attention | All Environments | Upstash QStash 服务的当前签名密钥，用于验证请求确实来自 QStash，防止伪造请求。 |
| `DEBUG` | Active | All Environments | 是否开启调试模式。在生产环境中应设置为 `false`，以避免泄漏敏感错误信息。 |
| `GITHUB_TOKEN` | Needs Attention | All Environments | GitHub Personal Access Token。用于授权后端通过 API 向您的 Hugo 博客仓库（如提交 Markdown 和图片）进行推送。需要勾选 `repo` 权限。 |
| `GITHUB_USERNAME` | Active | All Environments | 您的 GitHub 用户名（非邮箱），指定上述 Token 操作所对应的用户身份。 |
| `GITHUB_REPO` | Active | All Environments | 您的 Hugo 博客所在的 GitHub 仓库名称（例如：`hugo-blog`）。 |
| `SECRET_KEY` | Needs Attention | All Environments | 后端应用的安全密钥（用于 Session 等安全签名），建议配置为一个复杂的随机字符串（如 32 位以上）。 |
| `FRONTEND_URL` | Active | All Environments | 允许跨域（CORS）访问的前端地址。可以配置为具体的 Cloudflare Pages URL（例如 `https://hugo-blog-publisher.pages.dev`），或暂时填 `*` 允许所有。 |

---

## 修改与排查指南

### 如何在 Vercel 中修改环境变量？

1. 登录 [Vercel Dashboard](https://vercel.com/)。
2. 找到并点击进入您的项目。
3. 点击顶部的 **Settings** 选项卡。
4. 在左侧菜单中点击 **Environment Variables**。
5. 找到对应的变量（标记为 `Needs Attention` 通常意味着未设置、值为空或者已失效，需要重新更新）。
6. 点击变量右侧的三个点菜单选择 **Edit** 进行修改，或直接在页面上方重新添加同名变量覆盖旧值。
7. **注意**：修改环境变量后，通常需要进入 **Deployments** 页面，手动触发一次 **Redeploy**，新变量才会生效。

### 特别说明

- **QStash 相关 (`QSTASH_TOKEN` & `QSTASH_CURRENT_SIGNING_KEY`)**: 
  如果您的后端引入了消息队列或定时发布功能，需要在 [Upstash 控制台](https://console.upstash.com/) 中获取这两个值。如果您不需要相关功能，可以暂时忽略或从代码中移除依赖。
- **GitHub 相关 (`GITHUB_TOKEN` 等)**:
  若遇到 "GitHub 上传失败"，请优先检查 `GITHUB_TOKEN` 是否过期。如果过期，请到 GitHub -> Settings -> Developer settings 重新生成并在此处更新。
- **DeepSeek 模型**:
  项目中已配置为使用 `deepseek-v4-flash` 模型，如果需要可以在此页面额外配置 `DEEPSEEK_MODEL`。