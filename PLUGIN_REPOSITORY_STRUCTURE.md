# 插件仓库结构设计

## 概述

为了支持远程插件生态系统，我们需要建立**双仓库架构**：
1. **主仓库** (`universal-manga-downloader`) - 核心应用 + 内置插件
2. **插件仓库** (`umd-plugins`) - 社区插件 + 插件市场索引

参考成功案例：
- [Oh My Zsh](https://github.com/ohmyzsh/ohmyzsh) - 主程序 + [插件仓库](https://github.com/ohmyzsh/ohmyzsh/wiki/Plugins)
- [Obsidian Community Plugins](https://github.com/obsidianmd/obsidian-releases/blob/master/community-plugins.json)
- [VS Code Extensions](https://marketplace.visualstudio.com/vscode)

## 进度追踪（与 `REMOTE_PLUGIN_ROADMAP.md` 联动）

> 规则：完成阶段后将 `[ ]` 改为 `[x]`，并对阶段名称使用 `~~Phase X~~`，方便与主 Roadmap 的 v0.x 记录互相参照。

- [x] ~~Phase 1~~：仓库初始化（README、目录骨架、示例插件 3 个） → 依赖 `v0.1`。
- [x] ~~Phase 2~~：验证脚本、metadata、CI（validate + index） → 对应 `v0.2-v0.3`。
- [ ] Phase 3：GitHub Pages 市集（index.json、网站 UI、Copy URL） → 支撑 `v0.4`。
- [ ] Phase 4：多文件/依赖声明/信任等级 → 服务 `v0.5+`。

所有阶段完成情况应回写到 `REMOTE_PLUGIN_ROADMAP.md` 的迭代追踪板，保持主仓与插件仓同步滚动。

---

## 仓库架构

### 方案 A：单一插件仓库（推荐 v0.1-v0.3）

```
主仓库: github.com/cwlum/universal-manga-downloader
  ├── plugins/               # 内置官方插件
  │   ├── base.py
  │   ├── mangadex_parser.py
  │   ├── bato_parser.py
  │   ├── cbz_converter.py
  │   └── pdf_converter.py
  └── docs/
      └── PLUGINS.md         # 指向插件仓库

插件仓库: github.com/umd-plugins/official
  ├── README.md              # 插件市场首页
  ├── index.json             # 插件索引（v0.4 使用）
  ├── parsers/               # 解析器插件
  │   ├── manganato_parser.py
  │   ├── mangakakalot_parser.py
  │   └── webtoons_parser.py
  ├── converters/            # 转换器插件
  │   ├── epub_converter.py
  │   ├── mobi_converter.py
  │   └── png_to_jpg_converter.py
  ├── scripts/               # 自动化脚本
  │   ├── validate_plugin.py
  │   └── generate_index.py
  ├── docs/                  # 插件文档
  │   ├── submission-guide.md
  │   └── api-reference.md
  └── .github/
      └── workflows/
          └── validate-plugin.yml
```

**优点**：
- 结构清晰，易于管理
- GitHub Pages 可直接托管插件市场
- 社区贡献流程简单（PR 到插件仓库）

---

## 主仓库改动

### 1. 更新 README.md

在 `README.md` 添加插件相关章节：

```markdown
## Plugins

UMD ships with **4 built-in plugins**:
- **MangaDex Parser** - Extract chapters from mangadex.org
- **Bato Parser** - Extract chapters from bato.to/bato.si
- **CBZ Converter** - Package chapters as `.cbz` archives
- **PDF Converter** - Package chapters as `.pdf` documents

### Community Plugins

Browse and install **100+ community plugins** from our [Plugin Repository](https://github.com/umd-plugins/official):

| Plugin | Type | Description | Install |
| --- | --- | --- | --- |
| [Manganato Parser](https://github.com/umd-plugins/official/blob/main/parsers/manganato_parser.py) | Parser | Support for Manganato.com | [📋 Copy URL](#) |
| [EPUB Converter](https://github.com/umd-plugins/official/blob/main/converters/epub_converter.py) | Converter | Export as EPUB ebooks | [📋 Copy URL](#) |

**👉 [View All Plugins →](https://umd-plugins.github.io/official/)**

### Installing Remote Plugins

> 🚧 **Feature available in v1.4.0+** (currently in beta)

1. Open **Settings** tab → **Remote Plugins** section
2. Click **"Install from URL"**
3. Paste the GitHub raw URL (e.g., `https://raw.githubusercontent.com/umd-plugins/official/main/parsers/manganato_parser.py`)
4. Click **Install** and restart the app

Learn more: [Remote Plugin Guide](docs/REMOTE_PLUGINS.md)
```

### 2. 添加插件文档

创建 `docs/REMOTE_PLUGINS.md`：

```markdown
# Remote Plugin Installation Guide

## Quick Start

1. **Find a plugin** - Browse the [Plugin Repository](https://github.com/umd-plugins/official)
2. **Copy raw URL** - Click the "Raw" button on GitHub to get the URL
3. **Install in UMD**:
   - Open Settings → Remote Plugins
   - Paste URL and click Install
4. **Enable** - Toggle the plugin on in Settings → Plugins

## Safety Guidelines

⚠️ **Only install plugins from trusted sources!**

- Official repository: `github.com/umd-plugins/official`
- Verify the plugin code before installing
- Check for community reviews and ratings

## Troubleshooting

### "Invalid URL" error
- Ensure you're using the **raw** URL (starts with `raw.githubusercontent.com`)
- Example: `https://raw.githubusercontent.com/umd-plugins/official/main/parsers/example.py`

### "Dependency missing" error
- Install required packages: `pip install <package-name>`
- Check plugin documentation for dependency list

### Plugin not showing up
- Restart the application after installation
- Check Settings → Plugins to enable it

## Creating Your Own Plugins

See [Plugin Development Guide](../PLUGINS.md) for creating custom plugins.

To submit to the official repository, follow the [Submission Guide](https://github.com/umd-plugins/official/blob/main/docs/submission-guide.md).
```

### 3. 更新 PLUGINS.md

在现有的 `PLUGINS.md` 末尾添加：

```markdown
## Sharing Your Plugin

### Option 1: Personal Repository (Quick)

1. Create a GitHub repo (e.g., `my-umd-plugins`)
2. Add your plugin file (e.g., `awesome_parser.py`)
3. Share the raw URL with users:
   ```
   https://raw.githubusercontent.com/yourname/my-umd-plugins/main/awesome_parser.py
   ```

### Option 2: Official Repository (Recommended)

Submit to [umd-plugins/official](https://github.com/umd-plugins/official) for:
- ✅ Visibility in the Plugin Market
- ✅ Automated validation and testing
- ✅ Version management and updates
- ✅ Community ratings and reviews

**Submission Process**:
1. Fork `umd-plugins/official`
2. Add your plugin to `parsers/` or `converters/`
3. Run `python scripts/validate_plugin.py your_plugin.py`
4. Submit a PR with title `[Plugin] Add YourPluginName`

See [Submission Guide](https://github.com/umd-plugins/official/blob/main/docs/submission-guide.md) for details.
```

---

## 插件仓库设计

### 创建新仓库

**仓库名称**: `umd-plugins/official`
**描述**: Official plugin repository for Universal Manga Downloader
**URL**: `https://github.com/umd-plugins/official`

### 完整目录结构

```
umd-plugins/official/
├── README.md                      # 插件市场首页
├── LICENSE                        # MIT License
├── .gitignore
│
├── parsers/                       # 解析器目录
│   ├── README.md                  # 解析器列表
│   ├── manganato_parser.py
│   ├── mangakakalot_parser.py
│   ├── webtoons_parser.py
│   ├── mangafire_parser.py
│   └── asurascans_parser.py
│
├── converters/                    # 转换器目录
│   ├── README.md                  # 转换器列表
│   ├── epub_converter.py
│   ├── mobi_converter.py
│   ├── png_to_jpg_converter.py
│   └── webp_converter.py
│
├── index.json                     # 插件索引（v0.4）
│
├── scripts/                       # 自动化工具
│   ├── validate_plugin.py         # 插件验证脚本
│   ├── generate_index.py          # 生成 index.json
│   ├── calculate_checksum.py      # 计算 SHA-256
│   └── update_stats.py            # 更新下载统计
│
├── docs/                          # 文档
│   ├── submission-guide.md        # 提交指南
│   ├── api-reference.md           # API 文档
│   ├── testing-checklist.md       # 测试清单
│   └── security-review.md         # 安全审核标准
│
├── .github/                       # GitHub 配置
│   ├── workflows/
│   │   ├── validate-plugin.yml    # PR 自动验证
│   │   ├── generate-index.yml     # 自动生成索引
│   │   └── deploy-pages.yml       # 部署 GitHub Pages
│   ├── ISSUE_TEMPLATE/
│   │   ├── plugin_submission.md   # 插件提交模板
│   │   └── bug_report.md          # Bug 报告
│   └── pull_request_template.md   # PR 模板
│
└── website/                       # GitHub Pages 网站
    ├── index.html                 # 插件市场主页
    ├── styles.css
    ├── app.js                     # 动态加载插件列表
    └── assets/
        ├── logo.png
        └── screenshots/
```

---

## README.md 设计

### 插件仓库 README

```markdown
# Universal Manga Downloader - Official Plugin Repository

[![Plugin Count](https://img.shields.io/badge/plugins-24-blue)](https://umd-plugins.github.io/official/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Official plugin repository for [Universal Manga Downloader](https://github.com/cwlum/universal-manga-downloader).

## 🔌 Browse Plugins

**👉 [View Plugin Market](https://umd-plugins.github.io/official/)** (Interactive web interface)

Or browse by category:
- [**Parsers**](parsers/) - 15 site parsers
- [**Converters**](converters/) - 9 output formats

## 🚀 Quick Install

### Method 1: One-Click Install (v1.4.0+)

1. Browse the [Plugin Market](https://umd-plugins.github.io/official/)
2. Click **"Copy Install URL"** next to your desired plugin
3. In UMD: **Settings** → **Remote Plugins** → **Install from URL**
4. Paste and click **Install**

### Method 2: Manual Install

```bash
# Copy raw URL from GitHub (e.g., parsers/manganato_parser.py)
# In UMD Settings, paste:
https://raw.githubusercontent.com/umd-plugins/official/main/parsers/manganato_parser.py
```

## 📦 Featured Plugins

### Parsers

| Plugin | Sites Supported | Downloads | Install URL |
| --- | --- | --- | --- |
| **Manganato** | manganato.com, manganelo.com | 1.2k | [📋 Copy](https://raw.githubusercontent.com/umd-plugins/official/main/parsers/manganato_parser.py) |
| **Webtoons** | webtoons.com | 856 | [📋 Copy](https://raw.githubusercontent.com/umd-plugins/official/main/parsers/webtoons_parser.py) |
| **MangaFire** | mangafire.to | 623 | [📋 Copy](https://raw.githubusercontent.com/umd-plugins/official/main/parsers/mangafire_parser.py) |

### Converters

| Plugin | Format | Downloads | Install URL |
| --- | --- | --- | --- |
| **EPUB** | `.epub` (e-book) | 2.1k | [📋 Copy](https://raw.githubusercontent.com/umd-plugins/official/main/converters/epub_converter.py) |
| **MOBI** | `.mobi` (Kindle) | 1.5k | [📋 Copy](https://raw.githubusercontent.com/umd-plugins/official/main/converters/mobi_converter.py) |
| **WebP** | `.webp` (compression) | 432 | [📋 Copy](https://raw.githubusercontent.com/umd-plugins/official/main/converters/webp_converter.py) |

[**View All Plugins →**](https://umd-plugins.github.io/official/)

## 🛠️ Submit Your Plugin

We welcome community contributions! Follow these steps:

1. **Develop** - Create your plugin following the [API Reference](docs/api-reference.md)
2. **Test** - Run validation: `python scripts/validate_plugin.py your_plugin.py`
3. **Submit** - Open a PR with title `[Plugin] Add YourPluginName`
4. **Review** - Maintainers will review for security and functionality

See [Submission Guide](docs/submission-guide.md) for detailed instructions.

## 📖 Documentation

- [Submission Guide](docs/submission-guide.md) - How to contribute plugins
- [API Reference](docs/api-reference.md) - Plugin interface documentation
- [Testing Checklist](docs/testing-checklist.md) - Ensure plugin quality
- [Security Review](docs/security-review.md) - Security standards

## 🔒 Security

All plugins are reviewed by maintainers before merging. However:

- ⚠️ **Always review plugin code** before installing
- ✅ Only install from trusted sources
- 📢 Report security issues to [security@example.com](mailto:security@example.com)

## 📊 Statistics

- **Total Plugins**: 24
- **Total Downloads**: 12.4k
- **Contributors**: 18
- **Last Updated**: 2025-01-29

## 📝 License

All plugins in this repository are licensed under the [MIT License](LICENSE).
```

---

## GitHub Pages 插件市场

### index.html (交互式插件浏览器)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UMD Plugin Market</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>🔌 Universal Manga Downloader</h1>
            <h2>Plugin Market</h2>
            <p>Browse and install community plugins</p>
        </div>
    </header>

    <main class="container">
        <!-- 搜索和筛选 -->
        <section class="filters">
            <input type="text" id="search" placeholder="Search plugins...">
            <select id="type-filter">
                <option value="all">All Types</option>
                <option value="parser">Parsers</option>
                <option value="converter">Converters</option>
            </select>
            <select id="sort">
                <option value="downloads">Most Downloads</option>
                <option value="name">Name (A-Z)</option>
                <option value="updated">Recently Updated</option>
            </select>
        </section>

        <!-- 插件列表 -->
        <section id="plugin-grid" class="plugin-grid">
            <!-- 动态加载 -->
        </section>
    </main>

    <footer>
        <p>
            <a href="https://github.com/umd-plugins/official">GitHub Repository</a> |
            <a href="docs/submission-guide.md">Submit Plugin</a> |
            <a href="https://github.com/cwlum/universal-manga-downloader">Main Project</a>
        </p>
    </footer>

    <script src="app.js"></script>
</body>
</html>
```

### app.js (动态加载插件)

```javascript
// 从 index.json 加载插件数据
async function loadPlugins() {
    const response = await fetch('index.json');
    const data = await response.json();
    return data.plugins;
}

// 渲染插件卡片
function renderPlugin(plugin) {
    const rawUrl = `https://raw.githubusercontent.com/umd-plugins/official/main/${plugin.type}s/${plugin.id}.py`;

    return `
        <div class="plugin-card" data-type="${plugin.type}">
            <div class="plugin-header">
                <h3>${plugin.name}</h3>
                <span class="badge ${plugin.type}">${plugin.type}</span>
            </div>
            <p class="plugin-desc">${plugin.description}</p>
            <div class="plugin-meta">
                <span>📦 ${plugin.downloads.toLocaleString()} downloads</span>
                <span>⭐ ${plugin.rating}/5.0</span>
            </div>
            <div class="plugin-author">
                <small>by ${plugin.author} • v${plugin.version}</small>
            </div>
            <div class="plugin-actions">
                <button onclick="copyInstallUrl('${rawUrl}')" class="btn-primary">
                    📋 Copy Install URL
                </button>
                <a href="${plugin.repository}" class="btn-secondary" target="_blank">
                    View Code
                </a>
            </div>
        </div>
    `;
}

// 复制安装 URL
function copyInstallUrl(url) {
    navigator.clipboard.writeText(url).then(() => {
        showToast('✅ Install URL copied! Paste in UMD Settings → Remote Plugins');
    });
}

// 显示提示
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 100);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 搜索和筛选
function filterPlugins() {
    const search = document.getElementById('search').value.toLowerCase();
    const type = document.getElementById('type-filter').value;
    const cards = document.querySelectorAll('.plugin-card');

    cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        const cardType = card.dataset.type;

        const matchesSearch = text.includes(search);
        const matchesType = type === 'all' || cardType === type;

        card.style.display = matchesSearch && matchesType ? 'block' : 'none';
    });
}

// 初始化
async function init() {
    const plugins = await loadPlugins();
    const grid = document.getElementById('plugin-grid');

    grid.innerHTML = plugins.map(renderPlugin).join('');

    // 绑定事件
    document.getElementById('search').addEventListener('input', filterPlugins);
    document.getElementById('type-filter').addEventListener('change', filterPlugins);
}

init();
```

### styles.css (样式)

```css
:root {
    --primary: #007acc;
    --secondary: #5c5c5c;
    --bg: #1e1e1e;
    --card-bg: #2b2b2b;
    --text: #d4d4d4;
    --border: #3b3b3b;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

header {
    background: linear-gradient(135deg, #007acc 0%, #005a9e 100%);
    color: white;
    text-align: center;
    padding: 3rem 0;
}

header h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}

header h2 {
    font-size: 1.5rem;
    font-weight: normal;
    opacity: 0.9;
}

.filters {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
}

.filters input,
.filters select {
    padding: 0.75rem;
    border: 1px solid var(--border);
    background: var(--card-bg);
    color: var(--text);
    border-radius: 4px;
    font-size: 1rem;
}

.filters input {
    flex: 1;
}

.plugin-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 1.5rem;
}

.plugin-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
    transition: transform 0.2s, box-shadow 0.2s;
}

.plugin-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
    border-color: var(--primary);
}

.plugin-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.plugin-header h3 {
    font-size: 1.25rem;
    color: var(--primary);
}

.badge {
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: bold;
    text-transform: uppercase;
}

.badge.parser {
    background: #16825d;
    color: white;
}

.badge.converter {
    background: #cc6633;
    color: white;
}

.plugin-desc {
    color: #999;
    margin-bottom: 1rem;
    line-height: 1.5;
}

.plugin-meta {
    display: flex;
    gap: 1rem;
    font-size: 0.875rem;
    color: #888;
    margin-bottom: 0.5rem;
}

.plugin-author {
    font-size: 0.75rem;
    color: #666;
    margin-bottom: 1rem;
}

.plugin-actions {
    display: flex;
    gap: 0.75rem;
}

.btn-primary,
.btn-secondary {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    text-decoration: none;
    display: inline-block;
    text-align: center;
    transition: background 0.2s;
}

.btn-primary {
    background: var(--primary);
    color: white;
    flex: 1;
}

.btn-primary:hover {
    background: #005a9e;
}

.btn-secondary {
    background: var(--secondary);
    color: white;
}

.btn-secondary:hover {
    background: #404040;
}

.toast {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    background: #16825d;
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    opacity: 0;
    transform: translateY(20px);
    transition: all 0.3s;
    z-index: 1000;
}

.toast.show {
    opacity: 1;
    transform: translateY(0);
}

footer {
    text-align: center;
    padding: 2rem;
    color: #888;
}

footer a {
    color: var(--primary);
    text-decoration: none;
}

footer a:hover {
    text-decoration: underline;
}

@media (max-width: 768px) {
    .plugin-grid {
        grid-template-columns: 1fr;
    }

    .filters {
        flex-direction: column;
    }
}
```

---

## 自动化脚本

### scripts/validate_plugin.py

```python
#!/usr/bin/env python3
"""验证插件是否符合规范"""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
import sys
from pathlib import Path


def validate_plugin(file_path: Path) -> tuple[bool, list[str]]:
    """
    验证插件文件

    Returns:
        (is_valid, errors)
    """
    errors = []

    # 1. 检查文件存在
    if not file_path.exists():
        return False, [f"File not found: {file_path}"]

    # 2. 读取内容
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    # 3. 检查编码声明
    if not content.startswith("from __future__ import annotations"):
        errors.append("Missing 'from __future__ import annotations' at top")

    # 4. 检查元数据
    if not re.search(r'""".*?Name:.*?"""', content, re.DOTALL):
        errors.append("Missing metadata docstring (Name, Author, Version, etc.)")

    # 5. 检查基类导入
    has_base_plugin = "BasePlugin" in content
    has_base_converter = "BaseConverter" in content

    if not (has_base_plugin or has_base_converter):
        errors.append("Must import BasePlugin or BaseConverter from plugins.base")

    # 6. 语法检查
    try:
        ast.parse(content)
    except SyntaxError as e:
        errors.append(f"Syntax error: {e}")

    # 7. 检查类定义
    class_pattern = r"class\s+(\w+)\s*\(\s*(BasePlugin|BaseConverter)\s*\)"
    if not re.search(class_pattern, content):
        errors.append("No valid plugin class found (must inherit BasePlugin or BaseConverter)")

    # 8. 检查必需方法
    if has_base_plugin:
        required = ["get_name", "can_handle", "parse"]
        for method in required:
            if f"def {method}" not in content:
                errors.append(f"Missing required method: {method}")

    if has_base_converter:
        required = ["get_name", "get_output_extension", "convert"]
        for method in required:
            if f"def {method}" not in content:
                errors.append(f"Missing required method: {method}")

    # 9. 计算校验和
    checksum = hashlib.sha256(content.encode()).hexdigest()
    print(f"✓ Checksum: sha256:{checksum}")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="Validate UMD plugin")
    parser.add_argument("file", type=Path, help="Plugin file to validate")
    args = parser.parse_args()

    print(f"Validating {args.file}...")
    is_valid, errors = validate_plugin(args.file)

    if is_valid:
        print("✅ Plugin is valid!")
        return 0
    else:
        print("\n❌ Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

### scripts/generate_index.py

```python
#!/usr/bin/env python3
"""生成 index.json 插件索引"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


def parse_metadata(content: str) -> dict:
    """从插件代码提取元数据"""
    metadata = {}

    # 提取 docstring
    match = re.search(r'^"""(.*?)"""', content, re.DOTALL | re.MULTILINE)
    if not match:
        return metadata

    docstring = match.group(1)

    # 解析字段
    patterns = {
        "name": r"Name:\s*(.+)",
        "author": r"Author:\s*(.+)",
        "version": r"Version:\s*(.+)",
        "description": r"Description:\s*(.+)",
        "repository": r"Repository:\s*(.+)",
        "license": r"License:\s*(.+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, docstring)
        if match:
            metadata[key] = match.group(1).strip()

    # 依赖项
    deps_match = re.search(r"Dependencies:\s*(.+?)(?:\n\n|\Z)", docstring, re.DOTALL)
    if deps_match:
        deps_str = deps_match.group(1).strip()
        metadata["dependencies"] = [d.strip() for d in re.split(r"[,\n]", deps_str) if d.strip()]
    else:
        metadata["dependencies"] = []

    return metadata


def generate_index():
    """生成插件索引"""
    plugins = []

    # 扫描 parsers/
    for file in Path("parsers").glob("*.py"):
        if file.name.startswith("_"):
            continue

        content = file.read_text(encoding="utf-8")
        metadata = parse_metadata(content)
        checksum = hashlib.sha256(content.encode()).hexdigest()

        plugins.append({
            "id": file.stem,
            "name": metadata.get("name", file.stem.replace("_", " ").title()),
            "type": "parser",
            "author": metadata.get("author", "Unknown"),
            "version": metadata.get("version", "1.0.0"),
            "description": metadata.get("description", ""),
            "source_url": f"https://raw.githubusercontent.com/umd-plugins/official/main/parsers/{file.name}",
            "repository": metadata.get("repository", ""),
            "license": metadata.get("license", "MIT"),
            "tags": [],
            "dependencies": metadata.get("dependencies", []),
            "checksum": f"sha256:{checksum}",
            "downloads": 0,
            "rating": 5.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })

    # 扫描 converters/
    for file in Path("converters").glob("*.py"):
        if file.name.startswith("_"):
            continue

        content = file.read_text(encoding="utf-8")
        metadata = parse_metadata(content)
        checksum = hashlib.sha256(content.encode()).hexdigest()

        plugins.append({
            "id": file.stem,
            "name": metadata.get("name", file.stem.replace("_", " ").title()),
            "type": "converter",
            "author": metadata.get("author", "Unknown"),
            "version": metadata.get("version", "1.0.0"),
            "description": metadata.get("description", ""),
            "source_url": f"https://raw.githubusercontent.com/umd-plugins/official/main/converters/{file.name}",
            "repository": metadata.get("repository", ""),
            "license": metadata.get("license", "MIT"),
            "tags": [],
            "dependencies": metadata.get("dependencies", []),
            "checksum": f"sha256:{checksum}",
            "downloads": 0,
            "rating": 5.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })

    # 生成索引文件
    index = {
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "plugins": plugins
    }

    Path("index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Generated index.json with {len(plugins)} plugins")


if __name__ == "__main__":
    generate_index()
```

---

## GitHub Actions 工作流

### .github/workflows/validate-plugin.yml

```yaml
name: Validate Plugin Submission

on:
  pull_request:
    paths:
      - 'parsers/**'
      - 'converters/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Find changed files
        id: changed-files
        uses: tj-actions/changed-files@v44
        with:
          files: |
            parsers/*.py
            converters/*.py

      - name: Validate plugins
        run: |
          for file in ${{ steps.changed-files.outputs.all_changed_files }}; do
            echo "Validating $file..."
            python scripts/validate_plugin.py "$file"
          done

      - name: Check for malicious code
        run: |
          # 简单的静态分析
          for file in ${{ steps.changed-files.outputs.all_changed_files }}; do
            if grep -E "(exec|eval|__import__|compile|os\.system)" "$file"; then
              echo "⚠️ Warning: Potentially dangerous code found in $file"
              exit 1
            fi
          done
```

### .github/workflows/generate-index.yml

```yaml
name: Generate Plugin Index

on:
  push:
    branches: [main]
    paths:
      - 'parsers/**'
      - 'converters/**'

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Generate index
        run: python scripts/generate_index.py

      - name: Commit index
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add index.json
          git diff --quiet && git diff --staged --quiet || git commit -m "Update plugin index [skip ci]"
          git push
```

### .github/workflows/deploy-pages.yml

```yaml
name: Deploy GitHub Pages

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pages: write
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: 'website'

      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
```

---

## 实施步骤

### Phase 1: 建立插件仓库 (1-2天)

- [x] 建立 `umd-plugins/official` 仓库并同步到组织 (`git clone`, 初始化远端)。
- [x] 初始化目录骨架：`parsers/`, `converters/`, `scripts/`, `docs/`, `website/`, `.github/workflows/`。
- [x] 提交首版 README + `validate_plugin.py` + `generate_index.py`。
- [x] 配置 `validate-plugin.yml` 与 `generate-index.yml` 工作流。

### Phase 2: 迁移示例插件 (半天)

- [x] 复制/整理 3-5 个官方示例插件（含 metadata）。
- [x] 运行 `python scripts/validate_plugin.py <file>` 确认全部通过。
- [x] 生成 `index.json` 并推送，供 v0.4 市集预览。

### Phase 3: 建立 GitHub Pages (1天)

- [x] 完成本地 `website/index.html`, `styles.css`, `app.js` 版本。
- [x] 配置 `deploy-pages.yml` 并在 Settings→Pages 设为 GitHub Actions。
- [ ] 发布后验证线上站点、搜索/筛选/复制 URL 功能。

### Phase 4: 更新主仓库文档 (半天)

- [x] 主仓 README 新增插件市场段落与链接。
- [x] 新建 `docs/REMOTE_PLUGINS.md` 并在 UI 中指向。
- [x] `PLUGINS.md` 增补「分享你的插件」章节及提交指引。

---

## 总结

### 优点

✅ **用户体验好**
- 可视化浏览插件
- 一键复制安装 URL
- 类似 VS Code 扩展商店

✅ **开发者友好**
- 自动验证和索引生成
- GitHub Actions 自动化
- 清晰的提交流程

✅ **安全性高**
- 代码审查流程
- 自动安全检查
- SHA-256 校验

✅ **可扩展性强**
- 分离主仓库和插件仓库
- 支持多个插件源
- 易于维护和升级

### 工作量估算

| 任务 | 时间 |
| --- | --- |
| 建立插件仓库 | 1-2天 |
| GitHub Pages 网站 | 1天 |
| 自动化脚本 | 1天 |
| 更新主仓库文档 | 半天 |
| **总计** | **3-4天** |

### 下一步

1. 先创建插件仓库的基础结构
2. 建立 GitHub Pages 插件市场
3. 并行开发主应用的远程安装功能（v0.1 MVP）
4. 在 v0.1 完成后，将两者集成测试

这样用户就可以：
1. 访问插件市场网站
2. 浏览和搜索插件
3. 点击"Copy Install URL"
4. 在 UMD Settings 中粘贴并安装
