# 今日头条视频 Hugo Shortcode

在 Hugo 博客文章中直接嵌入播放今日头条视频。

## 安装步骤

### 1. 复制 Shortcode 文件

将 `toutiao-video.html` 复制到你的 Hugo 博客的 shortcodes 目录：

```bash
cp toutiao-video.html /path/to/your/hugo-blog/layouts/shortcodes/
```

### 2. 配置 API 地址

在你的 Hugo 配置文件 `config.toml` 或 `hugo.toml` 中添加：

```toml
[params]
  toutiaoApiBase = "https://your-api-domain.com"  # 你的视频解析API地址
```

如果你使用 `config.yaml`:

```yaml
params:
  toutiaoApiBase: "https://your-api-domain.com"
```

### 3. 确保后端API已部署

视频解析需要后端API支持，确保你的 hugo-blog-publisher 后端已部署并可访问。

## 使用方法

在 Markdown 文章中使用：

```markdown
{{< toutiao-video url="https://m.toutiao.com/is/xxx/" >}}
```

### 参数说明

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| url | ✅ | - | 今日头条视频链接 |
| width | ❌ | 100% | 视频宽度 |
| autoplay | ❌ | false | 是否自动播放 |

### 示例

**基本用法：**
```markdown
{{< toutiao-video url="https://m.toutiao.com/is/_BrepdmrnH8/" >}}
```

**指定宽度：**
```markdown
{{< toutiao-video url="https://m.toutiao.com/is/_BrepdmrnH8/" width="80%" >}}
```

**自动播放（静音）：**
```markdown
{{< toutiao-video url="https://m.toutiao.com/is/_BrepdmrnH8/" autoplay="true" >}}
```

## 效果预览

- ✅ 自动解析今日头条视频链接
- ✅ 获取多清晰度视频源（自动选择最高清晰度）
- ✅ 显示视频封面图
- ✅ 显示视频标题和作者
- ✅ 优雅的加载动画
- ✅ 错误状态提示

## 注意事项

1. **跨域问题**: 确保你的API服务器配置了正确的CORS头，允许你的博客域名访问
2. **视频时效性**: 今日头条视频地址有时效限制，每次加载会重新解析
3. **网络环境**: 部分地区可能无法直接访问视频CDN

## API 响应格式

Shortcode 内部调用 `/api/video/parse` 接口，期望返回格式：

```json
{
  "success": true,
  "data": {
    "video_id": "v02910g10002d5qn9knog65p59fe6bi0",
    "title": "视频标题",
    "cover": "https://封面图URL",
    "author": "作者名",
    "videos": [
      {"quality": "720p", "url": "https://视频地址"},
      {"quality": "480p", "url": "https://视频地址"}
    ]
  }
}
```
