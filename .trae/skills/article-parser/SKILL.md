---
name: "article-parser"
description: "统一文章解析器 — 微信公众号 / 今日头条 / 小红书 / 知乎 → Markdown + macOS Vision OCR 图片文字识别。当用户要求从文章 URL 中解析/提取内容时自动调用。"
---

# 统一文章解析器 (Article Parser) — 微信 · 头条 · 小红书 · 知乎 + OCR

一站式解析微信公众号、今日头条、小红书、知乎等平台的文章，并支持 **macOS Vision OCR** 识别图片中的文字。

## 支持的平台

| 平台 | 解析方式 | 图片处理 |
|:----|:--------|:--------|
| 📱 **微信公众号** | DOM 解析 + 短图文/图片集 JS 解编码 | 自动绕过防盗链 (i0.wp.com) |
| 📰 **今日头条** | API 采集 (多端点自动切换) | 自动绕过防盗链 (i0.wp.com) |
| 📕 **小红书** | API 采集 (多端点自动切换) | 自动绕过防盗链 (i0.wp.com) |
| 💬 **知乎** | DOM 解析 (修复懒加载) | 原生图片地址 |
| 🌐 **通用网页** | HTML → Markdown 后备解析 | 任意网页 |

## 使用方法

### 基础解析

```bash
# 微信公众号
python3 src/article_parser_cli.py "https://mp.weixin.qq.com/s/xxxxxx"

# 今日头条
python3 src/article_parser_cli.py "https://www.toutiao.com/article/xxxxxx/"

# 小红书
python3 src/article_parser_cli.py "https://www.xiaohongshu.com/explore/xxxxxx"

# 知乎
python3 src/article_parser_cli.py "https://zhuanlan.zhihu.com/p/xxxxxx"
```

### 带 OCR 图片文字识别

在基础解析基础上，添加 `--with-ocr` 参数即可启用 macOS Vision OCR：

```bash
# 微信公众号 + OCR（识别文章图片中的文字）
python3 src/article_parser_cli.py "https://mp.weixin.qq.com/s/xxxxxx" --with-ocr

# 今日头条 + OCR
python3 src/article_parser_cli.py "https://www.toutiao.com/article/xxxxxx/" --with-ocr -o output.md

# 通用网页 + OCR（任何带图的网页都能用）
python3 src/article_parser_cli.py "https://example.com/article" --with-ocr
```

OCR 流程：
1. 从文章内容中提取所有图片 URL（支持 MD 语法、API 返回数据等）
2. 下载图片到本地临时目录
3. macOS Vision 框架识别图片中的中/英文文字
4. 将 OCR 结果嵌入到 Markdown 输出的末尾（按图片顺序排列）

### 输出格式

```bash
# 保存到文件
python3 src/article_parser_cli.py <URL> -o output.md

# JSON 格式输出
python3 src/article_parser_cli.py <URL> --json
```

## 架构说明

### 文件结构

```
src/
├── article_parser_cli.py     # CLI 入口（参数解析 + 输出）
├── web_scraper.py            # 核心抓取引擎（平台识别 + 分派 + 内容提取）
├── toutiao_api.py            # 今日头条 API 采集器
├── xiaohongshu_api.py        # 小红书 API 采集器
└── ocr_utils.py              # macOS Vision OCR 工具模块（新增）
```

### 数据流

```
用户输入 URL
    ↓
article_parser_cli.py
    ├── 解析参数 (--with-ocr, --json, -o)
    └── 调用 web_scraper.fetch_article_content_with_images()
            ↓
    web_scraper.py
        ├── 识别平台域名
        ├── 分派到对应处理器
        │   ├── _handle_wechat()    — 微信公众号
        │   ├── _handle_toutiao()   — 今日头条 (ToutiaoScraper)
        │   ├── _handle_xiaohongshu() — 小红书 (XiaohongshuScraper)
        │   ├── _handle_zhihu()     — 知乎
        │   └── _handle_generic()   — 通用后备
        ├── 提取图片URL列表
        └── 返回 {title, content, author, platform, image_urls, raw_data}
                ↓
    （可选）OCR 处理
        ├── 下载图片到本地
        ├── macOS Vision OCR 识别
        └── 嵌入OCR结果到Markdown
                ↓
    输出 Markdown / JSON
```

### OCR 工具模块 (`ocr_utils.py`)

基于 xhs-article-extractor 中的 macOS Vision OCR 代码提取通用化：

- `macos_ocr(image_path)` — 单张图片 OCR
- `ocr_image_batch(urls, output_dir)` — 批量下载 + OCR
- 支持中英文混排识别（Vision 框架原生支持）
- 仅在 macOS 系统上可用

**依赖安装：**
```bash
pip install pyobjc-framework-Vision pyobjc-framework-Cocoa pyobjc-framework-Quartz
```

## 常见问题

### 1. OCR 不可用 / ModuleNotFoundError
```
ModuleNotFoundError: No module named 'Vision'
```
→ 安装 pyobjc (仅 macOS):
```bash
pip install pyobjc-framework-Vision pyobjc-framework-Cocoa pyobjc-framework-Quartz
```

### 2. 微信公众号图片不显示
微信图片有防盗链，已自动使用 `i0.wp.com` 代理绕过。如果代理失效，可下载到本地查看。

### 3. 小红书/头条 API 抓取失败
脚本内置多个 API 端点自动切换 + 重试机制。如果多次失败：
- 检查网络连接
- 等待 60 秒后重试（有自动等待重试逻辑）
- 最终会回退到 DOM 解析模式

### 4. OCR 图片下载太慢
`--with-ocr` 模式下需要下载全部图片到本地。图片多的文章（>20张）可能需要较长时间。
可限制处理数量（建议不超过50张）。

## 扩展新平台

1. 在 `web_scraper.py` 的 `fetch_article_content()` 中添加域名判断
2. 编写 `_handle_xxx()` 函数，返回 `{title, content, author}`
3. OCR 自动生效：只要内容中包含 `![alt](url)` 格式的图片链接
