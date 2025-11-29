# Wiki-Based Plugin Repository Guide

**简化版插件仓库方案** - 使用 GitHub Wiki 而非独立组织

---

## 🎯 方案概述

相比创建独立的 GitHub 组织，这个方案直接使用你现有的项目 Wiki 来管理插件目录，大大简化了部署流程。

### 优势对比

| 方案 | 组织+GitHub Pages | **Wiki方案（推荐）** |
|------|-------------------|---------------------|
| 需要创建组织 | ✅ 是 | ❌ 否 |
| 需要配置CI/CD | ✅ 是 | ❌ 否 |
| 需要维护额外仓库 | ✅ 是 | ❌ 否 |
| 需要网页开发 | ✅ 是 | ❌ 否 |
| 用户可浏览插件 | ✅ 是 | ✅ 是 |
| 支持搜索 | ✅ 是 | ✅ 是（GitHub Wiki内置） |
| 部署时间 | 1-2天 | **10分钟** |

---

## 📁 目录结构

```
universal-manga-downloader/
├── plugins/                    # 现有插件目录
│   ├── parsers/               # 本地解析器
│   └── converters/            # 本地转换器
│
├── community-plugins/          # 新增：社区插件存放处
│   ├── parsers/
│   │   ├── manganato_parser.py
│   │   ├── webtoons_parser.py
│   │   └── README.md
│   ├── converters/
│   │   ├── epub_converter.py
│   │   ├── mobi_converter.py
│   │   └── README.md
│   └── index.json             # 插件索引（自动生成）
│
└── scripts/
    ├── validate_community_plugin.py  # 验证脚本
    └── generate_plugin_index.py      # 生成索引
```

**关键点**:
- `community-plugins/` 存放在主仓库中
- Wiki 用于展示和文档
- 插件仍通过 GitHub Raw URL 安装

---

## 🚀 快速开始（10分钟设置）

### 步骤 1: 创建插件目录（2分钟）

```bash
# 在项目根目录执行
mkdir -p community-plugins/parsers
mkdir -p community-plugins/converters
mkdir -p scripts

# 创建README
cat > community-plugins/README.md << 'EOF'
# Community Plugins

This directory contains community-contributed plugins for Universal Manga Downloader.

## Installation

Copy the raw URL of any plugin and install via UMD:

1. Settings → Remote Plugins
2. Paste the raw URL: `https://raw.githubusercontent.com/yourusername/universal-manga-downloader/main/community-plugins/parsers/your_plugin.py`
3. Click Install

## Contributing

See [Plugin Submission Guide](https://github.com/yourusername/universal-manga-downloader/wiki/Plugin-Submission-Guide) in our wiki.
EOF

# 创建初始索引
cat > community-plugins/index.json << 'EOF'
{
  "version": "1.0",
  "last_updated": "2025-01-29T00:00:00Z",
  "plugins": []
}
EOF
```

### 步骤 2: 添加验证脚本（3分钟）

```bash
cat > scripts/validate_community_plugin.py << 'EOF'
#!/usr/bin/env python3
"""Validate community plugin before accepting PR."""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
import sys
from pathlib import Path


def validate_plugin(file_path: Path) -> tuple[bool, list[str]]:
    """Validate plugin file structure and content."""
    errors = []

    if not file_path.exists():
        return False, [f"File not found: {file_path}"]

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    # Check Python syntax
    try:
        ast.parse(content)
    except SyntaxError as e:
        errors.append(f"Syntax error: {e}")

    # Check for future annotations
    if not content.startswith("from __future__ import annotations"):
        errors.append("Missing 'from __future__ import annotations' at top")

    # Check metadata docstring
    if not re.search(r'""".*?Name:.*?"""', content, re.DOTALL):
        errors.append("Missing metadata docstring with Name field")

    # Check base class
    has_base_plugin = "BasePlugin" in content
    has_base_converter = "BaseConverter" in content

    if not (has_base_plugin or has_base_converter):
        errors.append("Must import BasePlugin or BaseConverter")

    # Check class definition
    class_pattern = r"class\s+(\w+)\s*\(\s*(BasePlugin|BaseConverter)\s*\)"
    if not re.search(class_pattern, content):
        errors.append("No valid plugin class found")

    # Calculate checksum
    checksum = hashlib.sha256(content.encode()).hexdigest()
    print(f"✓ Checksum: sha256:{checksum}")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="Validate UMD community plugin")
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
EOF

chmod +x scripts/validate_community_plugin.py
```

### 步骤 3: 启用 Wiki（1分钟）

1. 访问 GitHub 仓库
2. **Settings** → **General** → **Features**
3. 勾选 **✅ Wikis**
4. 保存

### 步骤 4: 创建 Wiki 页面（4分钟）

访问你的 Wiki: `https://github.com/yourusername/universal-manga-downloader/wiki`

#### 创建主页面: `Home.md`

```markdown
# Universal Manga Downloader - Community Plugins

Browse and install community-contributed plugins for UMD.

## 📦 Available Plugins

### Parser Plugins

| Plugin | Version | Author | Description | Install URL |
|--------|---------|--------|-------------|-------------|
| Example Parser | 1.0.0 | Demo | Example site parser | [Copy URL](https://raw.githubusercontent.com/yourusername/universal-manga-downloader/main/community-plugins/parsers/example_parser.py) |

### Converter Plugins

| Plugin | Version | Author | Description | Install URL |
|--------|---------|--------|-------------|-------------|
| Example Converter | 1.0.0 | Demo | Example format converter | [Copy URL](https://raw.githubusercontent.com/yourusername/universal-manga-downloader/main/community-plugins/converters/example_converter.py) |

## 🚀 How to Install

1. Click the **Copy URL** link for the plugin you want
2. Open UMD → **Settings** → **Remote Plugins**
3. Paste the URL in the input field
4. Click **Install**

## 🛠️ Submit Your Plugin

See [Plugin Submission Guide](Plugin-Submission-Guide) for details.

---

**Last Updated**: 2025-01-29
```

#### 创建提交指南: `Plugin-Submission-Guide.md`

```markdown
# Plugin Submission Guide

## Requirements

- ✅ Single `.py` file (or ZIP for multi-file plugins)
- ✅ Inherits from `BasePlugin` or `BaseConverter`
- ✅ Contains complete metadata docstring
- ✅ Passes validation

## Metadata Format

```python
"""
Universal Manga Downloader Plugin

Name: Your Plugin Name
Author: Your Name
Version: 1.0.0
Description: Brief description of what your plugin does
Repository: https://github.com/yourname/your-repo
License: MIT
Dependencies: requests>=2.28.0, pillow>=10.0.0
"""
```

## Submission Steps

1. **Fork the repository**
   ```bash
   gh repo fork yourusername/universal-manga-downloader
   ```

2. **Add your plugin**
   ```bash
   # For parsers
   cp your_parser.py community-plugins/parsers/

   # For converters
   cp your_converter.py community-plugins/converters/
   ```

3. **Validate**
   ```bash
   python scripts/validate_community_plugin.py community-plugins/parsers/your_parser.py
   ```

4. **Create Pull Request**
   - Title: `[Plugin] Add YourPluginName`
   - Description: Explain what sites/formats your plugin supports
   - Include screenshots if applicable

5. **Wait for Review**
   - Maintainers will review your code for security
   - Once approved, it will be merged and appear in the wiki

## Review Checklist

- [ ] Plugin validates successfully
- [ ] No malicious code (exec, eval, os.system, etc.)
- [ ] Follows naming conventions
- [ ] Has complete metadata
- [ ] Works as described

---

Need help? [Open an issue](https://github.com/yourusername/universal-manga-downloader/issues)
```

---

## 📝 维护 Wiki（日常更新）

### 手动更新（推荐新插件时）

当新插件被合并到 `community-plugins/` 后：

1. 编辑 Wiki Home 页面
2. 在对应表格中添加一行：

```markdown
| YourPluginName | 1.0.0 | YourName | Parser for SomeWebsite | [Copy URL](https://raw.githubusercontent.com/.../your_plugin.py) |
```

3. 保存（Wiki自动提交）

### 自动更新（可选）

创建脚本自动生成 Wiki 表格：

```bash
cat > scripts/generate_wiki_table.py << 'EOF'
#!/usr/bin/env python3
"""Generate markdown table for wiki from community-plugins/."""

from __future__ import annotations

import re
from pathlib import Path


def parse_metadata(content: str) -> dict:
    """Extract metadata from plugin docstring."""
    metadata = {}
    match = re.search(r'^"""(.*?)"""', content, re.DOTALL | re.MULTILINE)
    if not match:
        return metadata

    docstring = match.group(1)
    patterns = {
        "name": r"Name:\s*(.+)",
        "author": r"Author:\s*(.+)",
        "version": r"Version:\s*(.+)",
        "description": r"Description:\s*(.+)",
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, docstring, re.IGNORECASE)
        if m:
            metadata[key] = m.group(1).strip()

    return metadata


def generate_table(plugin_type: str, directory: Path, repo_url: str) -> str:
    """Generate markdown table for given plugin type."""
    lines = [
        "| Plugin | Version | Author | Description | Install URL |",
        "|--------|---------|--------|-------------|-------------|",
    ]

    for file in sorted(directory.glob("*.py")):
        if file.name.startswith("_") or file.name == "README.md":
            continue

        content = file.read_text(encoding="utf-8")
        metadata = parse_metadata(content)

        name = metadata.get("name", file.stem.replace("_", " ").title())
        version = metadata.get("version", "1.0.0")
        author = metadata.get("author", "Unknown")
        description = metadata.get("description", "")

        raw_url = f"{repo_url}/main/community-plugins/{plugin_type}/{file.name}"
        lines.append(
            f"| {name} | {version} | {author} | {description} | [Copy URL]({raw_url}) |"
        )

    return "\n".join(lines)


def main():
    repo_url = "https://raw.githubusercontent.com/yourusername/universal-manga-downloader"

    print("### Parser Plugins\n")
    print(generate_table("parsers", Path("community-plugins/parsers"), repo_url))
    print("\n### Converter Plugins\n")
    print(generate_table("converters", Path("community-plugins/converters"), repo_url))


if __name__ == "__main__":
    main()
EOF

chmod +x scripts/generate_wiki_table.py
```

运行后复制输出到 Wiki。

---

## 🔄 工作流程对比

### 传统方案（组织+Pages）

```
开发者提交插件 PR
  ↓
GitHub Actions 验证
  ↓
合并到 umd-plugins/official
  ↓
自动生成 index.json
  ↓
自动部署 GitHub Pages
  ↓
用户在网页浏览并复制URL
  ↓
用户在UMD中粘贴URL安装
```

### Wiki方案（简化）

```
开发者提交插件 PR
  ↓
手动验证（python scripts/validate_community_plugin.py）
  ↓
合并到 community-plugins/
  ↓
更新 Wiki 表格（手动或脚本）
  ↓
用户在 Wiki 浏览并复制URL
  ↓
用户在UMD中粘贴URL安装
```

**省略的步骤**:
- ❌ 创建GitHub组织
- ❌ 配置GitHub Actions
- ❌ 开发网页界面
- ❌ 配置GitHub Pages

---

## 📊 功能对比

| 功能 | 组织方案 | Wiki方案 | 备注 |
|------|----------|----------|------|
| 插件浏览 | ✅ | ✅ | Wiki表格同样清晰 |
| 搜索插件 | ✅ | ✅ | Wiki内置搜索 |
| 一键安装 | ✅ | ✅ | 都是复制URL |
| 自动验证 | ✅ | 🟡 | Wiki需手动验证 |
| 自动更新索引 | ✅ | 🟡 | Wiki需手动更新 |
| 统计数据 | ✅ | ❌ | Wiki无下载统计 |
| 评分系统 | ✅ | ❌ | Wiki无评分 |
| 复杂度 | 高 | **低** | 关键优势 |
| 维护成本 | 高 | **低** | 关键优势 |

---

## 🎯 最佳实践

### 1. 插件命名规范

```
✅ 好的命名:
  - manganato_parser.py
  - webtoons_parser.py
  - epub_converter.py

❌ 避免:
  - parser.py
  - plugin1.py
  - my_awesome_plugin.py
```

### 2. Wiki 组织结构

```
Wiki Pages:
├── Home.md                      # 插件列表（主页）
├── Plugin-Submission-Guide.md   # 提交指南
├── Plugin-Development-FAQ.md    # 常见问题
└── Plugin-Security-Policy.md    # 安全政策
```

### 3. PR 审查流程

创建 PR 模板: `.github/PULL_REQUEST_TEMPLATE/plugin_submission.md`

```markdown
## Plugin Submission Checklist

- [ ] Plugin file added to `community-plugins/parsers/` or `community-plugins/converters/`
- [ ] Passes validation: `python scripts/validate_community_plugin.py <file>`
- [ ] Metadata complete (Name, Author, Version, Description)
- [ ] No dangerous code (exec, eval, os.system)
- [ ] Tested and works as described

### Plugin Information

**Name**:
**Type**: Parser / Converter
**Supports**: (e.g., manganato.com, webtoons.com)
**Dependencies**: (e.g., requests>=2.28.0)

### Description

<!-- Brief description of what your plugin does -->

### Testing

<!-- How did you test this plugin? -->
```

---

## 🔧 可选增强

### GitHub Actions 自动验证（可选）

即使使用Wiki方案，你仍可添加自动验证：

```yaml
# .github/workflows/validate-community-plugin.yml
name: Validate Community Plugin

on:
  pull_request:
    paths:
      - 'community-plugins/**'

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
            community-plugins/**/*.py

      - name: Validate plugins
        if: steps.changed-files.outputs.any_changed == 'true'
        run: |
          for file in ${{ steps.changed-files.outputs.all_changed_files }}; do
            echo "Validating $file..."
            python scripts/validate_community_plugin.py "$file"
          done

      - name: Check for dangerous code
        if: steps.changed-files.outputs.any_changed == 'true'
        run: |
          for file in ${{ steps.changed-files.outputs.all_changed_files }}; do
            if grep -E "(exec|eval|__import__|compile|os\.system)" "$file"; then
              echo "⚠️ Warning: Potentially dangerous code in $file"
              exit 1
            fi
          done
```

### 生成统计页面（可选）

```bash
cat > scripts/generate_stats.py << 'EOF'
#!/usr/bin/env python3
"""Generate plugin statistics for wiki."""

from pathlib import Path

parsers = list(Path("community-plugins/parsers").glob("*.py"))
converters = list(Path("community-plugins/converters").glob("*.py"))

print("## 📊 Plugin Statistics\n")
print(f"- **Total Plugins**: {len(parsers) + len(converters)}")
print(f"- **Parsers**: {len(parsers)}")
print(f"- **Converters**: {len(converters)}")
print(f"- **Last Updated**: {Path('community-plugins').stat().st_mtime}")
EOF

chmod +x scripts/generate_stats.py
```

---

## ✅ 完成检查清单

部署Wiki方案后，检查以下项目：

- [ ] `community-plugins/` 目录已创建
- [ ] `scripts/validate_community_plugin.py` 可用
- [ ] Wiki 已启用
- [ ] Wiki Home 页面包含插件列表
- [ ] Wiki 提交指南页面已创建
- [ ] 至少有1个示例插件
- [ ] PR模板已配置
- [ ] README.md 中链接到 Wiki
- [ ] 测试从Wiki复制URL安装插件成功

---

## 🆚 迁移建议

如果你已经按照 `PLUGIN_REPOSITORY_SETUP_GUIDE.md` 创建了组织：

### 从组织迁移到Wiki

```bash
# 1. 复制插件到主仓库
cp -r ../umd-plugins-official/parsers/* community-plugins/parsers/
cp -r ../umd-plugins-official/converters/* community-plugins/converters/

# 2. 更新remote_manager.py中的默认源
# 将:
DEFAULT_ALLOWED_SOURCES = (
    "https://raw.githubusercontent.com/umd-plugins/official/",
)
# 改为:
DEFAULT_ALLOWED_SOURCES = (
    "https://raw.githubusercontent.com/yourusername/universal-manga-downloader/main/community-plugins/",
)

# 3. 提交更改
git add community-plugins/ plugins/remote_manager.py
git commit -m "chore: migrate to wiki-based plugin repository"
git push
```

### 保留两种方案（混合）

你也可以同时保留：
- 官方插件 → Wiki方案（主仓库）
- 社区插件 → 组织方案（独立仓库）

在 `remote_manager.py` 中添加两个默认源：

```python
DEFAULT_ALLOWED_SOURCES = (
    "https://raw.githubusercontent.com/yourusername/universal-manga-downloader/main/community-plugins/",
    "https://raw.githubusercontent.com/umd-plugins/official/main/",
)
```

---

## 📚 总结

### Wiki方案适合你如果：

- ✅ 你想快速上线插件系统（10分钟 vs 2天）
- ✅ 你不想维护额外的组织和仓库
- ✅ 你的用户群较小，手动管理可接受
- ✅ 你更关注功能而非华丽界面

### 组织方案适合你如果：

- ✅ 你有大量插件需要管理（50+）
- ✅ 你需要自动化一切（CI/CD, 统计, 评分）
- ✅ 你有时间投入基础设施建设
- ✅ 你想要专业的插件市场体验

---

**推荐**: 从Wiki方案开始，当插件数量增长到20+个时再考虑迁移到组织方案。

**创建时间**: 2025-01-29
**维护者**: UMD Team
