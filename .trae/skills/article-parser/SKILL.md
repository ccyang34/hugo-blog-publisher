---
name: "article-parser"
description: "Parses articles from WeChat, Toutiao, Xiaohongshu, etc. into Markdown. Invoke when user asks to parse/extract content from an article URL."
---

# Article Parser

This skill allows you to independently extract and parse content from supported platforms (WeChat Official Accounts, Toutiao, Xiaohongshu, Zhihu, etc.) and convert them into clean Markdown format.

## When to use

- The user provides an article URL and asks you to "extract", "parse", "read", or "convert" it.
- The user wants to test the scraper logic on a specific link (e.g., "Parse this WeChat article for me").

## How to use

You can parse an article by invoking the `article_parser_cli.py` script provided in the backend codebase.

Run the following command in the terminal:

```bash
python3 backend/utils/article-parser-skill/article_parser_cli.py "<URL>"
```

### Options
- `--json`: Output the complete parsed result (title, content, author, etc.) in JSON format instead of plain Markdown.
- `--output <file>` or `-o <file>`: Save the output directly to a file.

### Examples

**Example 1: Print parsed Markdown directly to terminal**
```bash
python3 backend/utils/article-parser-skill/article_parser_cli.py "https://mp.weixin.qq.com/s/xxxxxx"
```

**Example 2: Output as JSON**
```bash
python3 backend/utils/article-parser-skill/article_parser_cli.py "https://www.xiaohongshu.com/explore/xxxxxx" --json
```

**Example 3: Save parsed result to a Markdown file**
```bash
python3 backend/utils/article-parser-skill/article_parser_cli.py "https://www.toutiao.com/article/xxxxxx/" -o output.md
```

## Supported Platforms
- **WeChat Official Accounts (微信公众号)**: Extracts text, images, and embedded video sources.
- **Toutiao (今日头条)**: Extracts standard articles and article metadata.
- **Xiaohongshu (小红书)**: Extracts title, description, tags, and images (bypasses some basic anti-scraping).
- **Zhihu (知乎)**: Extracts answers/articles with lazy-loaded images fixed.
- **Generic**: Fallback logic for generic blog posts or web articles.
