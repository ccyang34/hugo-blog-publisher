---
name: "article-parser"
description: "将微信、头条、小红书等平台的文章解析为 Markdown 格式。当用户要求从文章 URL 中解析/提取内容时调用此技能。"
---

# 文章解析器 (Article Parser)

此技能允许你独立提取并解析支持平台（微信公众号、今日头条、小红书、知乎等）的文章内容，并将其转换为干净的 Markdown 格式。

## 何时使用

- 当用户提供文章 URL 并要求你“提取”、“解析”、“读取”或“转换”它时。
- 当用户希望在特定链接上测试抓取逻辑时（例如，“帮我解析这篇微信文章”）。

## 如何使用

你可以通过调用后端代码库中提供的 `article_parser_cli.py` 脚本来解析文章。

在终端中运行以下命令：

```bash
python3 src/article_parser_cli.py "<URL>"
```

### 选项 (Options)
- `--json`：以 JSON 格式输出完整的解析结果（标题、内容、作者等），而不是纯 Markdown。
- `--output <file>` 或 `-o <file>`：将输出结果直接保存到文件中。

### 示例 (Examples)

**示例 1：将解析后的 Markdown 直接打印到终端**
```bash
python3 src/article_parser_cli.py "https://mp.weixin.qq.com/s/xxxxxx"
```

**示例 2：输出为 JSON 格式**
```bash
python3 src/article_parser_cli.py "https://www.xiaohongshu.com/explore/xxxxxx" --json
```

**示例 3：将解析结果保存到 Markdown 文件**
```bash
python3 src/article_parser_cli.py "https://www.toutiao.com/article/xxxxxx/" -o output.md
```

## 支持的平台 (Supported Platforms)
- **微信公众号 (WeChat Official Accounts)**: 提取文本、图片和嵌入的视频源。
- **今日头条 (Toutiao)**: 提取标准文章及文章元数据。
- **小红书 (Xiaohongshu)**: 提取标题、描述、标签和图片（绕过部分基础防爬限制）。
- **知乎 (Zhihu)**: 提取回答/文章内容，并修复图片懒加载。
- **通用 (Generic)**: 用于普通博客文章或网页文章的后备解析逻辑。