# 远程插件系统实现路线图

## 概述

本文档详细规划将 Universal Manga Downloader 的插件系统改造为支持从 GitHub 远程下载安装的完整方案。

### 当前状态
- ✅ 本地插件自动发现和加载
- ✅ 运行时启用/禁用插件
- ✅ 完善的基类抽象（BasePlugin、BaseConverter）
- ✅ 生命周期管理（on_load/on_unload）

### 目标状态
- 🎯 从 GitHub URL 一键安装插件
- 🎯 插件版本管理和更新
- 🎯 社区插件仓库浏览
- 🎯 安全性验证机制
- 🎯 依赖自动检测和提示

### 当前基线（v1.3.6）
- 现行 GUI 仍以 Tkinter (`ui/app.py`) 为核心；任何规划中的 PyQt 伪代码需折算成 Tkinter 控件或封装在独立工具窗口。
- `PluginManager` 支援自定义 `PluginLoader`，但默认流程只扫描本地 `plugins/`；远程方案必须保持与既有 Loader API 兼容。
- Python 版本锁定在 3.11.x，lint/typecheck 流程（`ruff`, `mypy`）与 `tests/` 中的集成测试必须持续通过。
- 当前发布版本 `v1.3.6` 的二进制与配置格式不可破坏；任何远端插件配置需向下兼容既有 `config.py` 与 `settings.json`。
- 应用在 macOS / Windows 均以离线模式交付，因此远端插件能力必须提供显式 opt-in 与回退路径，以免影响 `v1.3.6` 用户体验。

## 迭代追踪板（小版本滚动）

> 完成一个小版本后，将对应条目的 `[ ]` 改成 `[x]`，并对版本号使用 `~~vX.Y~~` 处理，方便一眼确认哪些阶段已交付。

| 版本 | 状态 | 目标日期 | 关键交付 | 依赖 |
| --- | --- | --- | --- | --- |
| - [x] ~~v0.1 MVP~~ | 完成 | 2025-11-29 | GitHub Raw 安装、registry v1、Tk UI 入口 | `PluginRepositoryStructure` Phase 1 |
| - [x] ~~v0.2 安全+UX~~ | 完成 | 2025-11-29 | Metadata/Checksum、白名单、Beta Flag | v0.1 ✔ |
| - [x] ~~v0.3 更新机制~~ | 完成 | 2025-11-29 | Version Manager、历史记录、回滚 | v0.2 ✔ |
| - [ ] v0.4 插件市场 | 开发中 | 2026-01-05 | 仓库索引 & UI、市集接口 | `PLUGIN_REPOSITORY_STRUCTURE` Phase 3 |
| - [ ] v0.5 依赖+多文件 | 规划中 | 2026-01-20 | Dependency Manager、ZIP 包支持 | v0.4 ✔ |

相关 wiki：`PLUGIN_REPOSITORY_STRUCTURE.md` 负责外部仓库、网站与自动化，两个文档需要同步更新交付状态。

---

## 版本迭代计划

### v0.1 - MVP（最小可用版本）
**工作量**: 3-5 天
**目标**: 实现基础的远程下载和安装功能

#### 功能清单
- [x] 核心功能
  - [ ] 从 GitHub raw URL 下载单个 `.py` 文件
  - [ ] 基础代码验证（检查是否继承正确的基类）
  - [ ] 保存到 `plugins/` 目录
  - [ ] 安装后自动加载插件
- [x] 数据存储
  - [ ] 创建 `plugin_registry.json` 记录已安装的远程插件
  - [ ] 记录字段：name、source_url、install_date、file_path
- [x] UI 集成
  - [ ] Settings 标签页新增"安装远程插件"按钮
  - [ ] 简单的 URL 输入对话框
  - [ ] 安装成功/失败提示

#### 前置条件（v0.1）
- `v1.3.6` 代码基必须保持可构建，且 `PluginManager` 仍由 Tkinter UI 初始化。
- 已执行 `requirements.txt` 安装与 `ruff`/`mypy` 乾净通过，确保远端功能不会掩盖现有 lint 警告。
- 为发布准备 `feature/remote-plugins-mvp` 分支并配置实验性 feature flag（例如 `CONFIG.features.remote_plugins = False`）。

#### 验收标准（v0.1）
- 可在 macOS/Windows 上透过单一 raw URL 成功安装解析器或转换器，并即时显示在 Settings 页面。
- `plugin_registry.json` 会随应用重启保持同步，且移除远程插件后不影响本地插件。
- `pytest tests/test_plugins -q` 与 `tests/test_integration.py` 全数通过，证明 Loader 兼容。
- 若远端下载失败，UI 会以非阻塞方式回报并留在安全状态（不写入半成品文件）。

#### 迭代任务清单（v0.1）
- [x] `feature/remote-plugins-mvp` 分支创建，CI 标记 `remote-plugin` 套餐。
- [x] `RemotePluginManager` MVP 与 registry v1（无 metadata）落地，并附带单元测试。
- [x] Settings→Remote Plugins Tk UI（URL 输入/Toast/错误提示）实现。
- [x] `PLUGIN_REPOSITORY_STRUCTURE` Phase 1 中的官方仓库 README/示例插件同步上线。

#### 技术实现

```python
# plugins/remote_manager.py (新文件)
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TypedDict
from urllib.request import urlopen

logger = logging.getLogger(__name__)

REGISTRY_FILE = Path("plugins/plugin_registry.json")


class RemotePluginInfo(TypedDict):
    """远程插件记录"""
    name: str
    source_url: str
    install_date: str
    file_path: str
    plugin_type: str  # "parser" | "converter"


class RemotePluginManager:
    """管理远程插件的下载和安装"""

    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir
        self.registry: list[RemotePluginInfo] = self._load_registry()

    def _load_registry(self) -> list[RemotePluginInfo]:
        """加载插件注册表"""
        if not REGISTRY_FILE.exists():
            return []
        try:
            with open(REGISTRY_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load registry: %s", e)
            return []

    def _save_registry(self) -> None:
        """保存插件注册表"""
        try:
            REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.registry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save registry: %s", e)

    def install_from_url(self, url: str) -> tuple[bool, str]:
        """
        从 GitHub raw URL 安装插件

        Args:
            url: GitHub raw URL (e.g., https://raw.githubusercontent.com/...)

        Returns:
            (success, message) 元组
        """
        try:
            # 1. 验证 URL 格式
            if not self._is_valid_github_url(url):
                return False, "无效的 GitHub URL，请使用 raw.githubusercontent.com 链接"

            # 2. 下载文件内容
            logger.info("Downloading plugin from %s", url)
            with urlopen(url, timeout=30) as response:
                content = response.read().decode("utf-8")

            # 3. 基础验证
            validation_result = self._validate_plugin_code(content)
            if not validation_result["valid"]:
                return False, f"插件验证失败: {validation_result['reason']}"

            # 4. 提取文件名
            filename = self._extract_filename(url)
            if not filename.endswith(".py"):
                filename += ".py"

            # 5. 检查是否已安装
            if self._is_installed(filename):
                return False, f"插件 {filename} 已安装，请先卸载旧版本"

            # 6. 保存文件
            file_path = self.plugin_dir / filename
            file_path.write_text(content, encoding="utf-8")
            logger.info("Saved plugin to %s", file_path)

            # 7. 记录到注册表
            self.registry.append(RemotePluginInfo(
                name=validation_result["plugin_name"],
                source_url=url,
                install_date=datetime.now().isoformat(),
                file_path=str(file_path),
                plugin_type=validation_result["plugin_type"]
            ))
            self._save_registry()

            return True, f"成功安装插件: {validation_result['plugin_name']}"

        except Exception as e:
            logger.error("Failed to install plugin: %s", e)
            return False, f"安装失败: {str(e)}"

    def _is_valid_github_url(self, url: str) -> bool:
        """验证是否为有效的 GitHub raw URL"""
        pattern = r"^https://raw\.githubusercontent\.com/[\w-]+/[\w-]+/.+\.py$"
        return bool(re.match(pattern, url))

    def _validate_plugin_code(self, code: str) -> dict:
        """
        验证插件代码

        检查:
        1. 是否包含 BasePlugin 或 BaseConverter 导入
        2. 是否定义了继承自基类的类
        3. 提取插件名称和类型
        """
        # 简单的静态分析
        has_base_plugin = "BasePlugin" in code
        has_base_converter = "BaseConverter" in code

        if not (has_base_plugin or has_base_converter):
            return {
                "valid": False,
                "reason": "代码中未找到 BasePlugin 或 BaseConverter 继承"
            }

        # 尝试提取类名
        class_pattern = r"class\s+(\w+)\s*\(\s*(BasePlugin|BaseConverter)\s*\)"
        match = re.search(class_pattern, code)

        if not match:
            return {
                "valid": False,
                "reason": "未找到有效的插件类定义"
            }

        class_name = match.group(1)
        base_class = match.group(2)
        plugin_type = "parser" if base_class == "BasePlugin" else "converter"

        return {
            "valid": True,
            "plugin_name": class_name,
            "plugin_type": plugin_type
        }

    def _extract_filename(self, url: str) -> str:
        """从 URL 提取文件名"""
        return url.rstrip("/").split("/")[-1]

    def _is_installed(self, filename: str) -> bool:
        """检查插件是否已安装"""
        return any(
            Path(record["file_path"]).name == filename
            for record in self.registry
        )

    def uninstall(self, plugin_name: str) -> tuple[bool, str]:
        """卸载远程安装的插件"""
        for record in self.registry:
            if record["name"] == plugin_name:
                try:
                    # 删除文件
                    file_path = Path(record["file_path"])
                    if file_path.exists():
                        file_path.unlink()

                    # 从注册表移除
                    self.registry.remove(record)
                    self._save_registry()

                    return True, f"成功卸载插件: {plugin_name}"
                except Exception as e:
                    return False, f"卸载失败: {str(e)}"

        return False, f"未找到插件: {plugin_name}"

    def list_installed(self) -> list[RemotePluginInfo]:
        """列出所有已安装的远程插件"""
        return self.registry.copy()
```

#### UI 代码示例

> ⚠️ 当前 `v1.3.6` GUI 基于 Tkinter，上述 PyQt6 示例仅用于描述交互流程。正式实现时需要在 `ui/tabs/settings_tab.py` 里以 Tk 组件（`ttk.Frame`, `tk.simpledialog` 等）重建同样的 UX，或封装成独立 Tk 窗口。

```python
# ui/tabs/settings_tab.py 新增部分
class SettingsTab:
    def _create_remote_plugin_section(self, parent: QWidget) -> QGroupBox:
        """创建远程插件管理区域"""
        group = QGroupBox("远程插件管理", parent)
        layout = QVBoxLayout(group)

        # 安装按钮
        install_btn = QPushButton("从 GitHub URL 安装插件")
        install_btn.clicked.connect(self._on_install_remote_plugin)
        layout.addWidget(install_btn)

        # 已安装列表
        self.remote_list = QListWidget()
        self._refresh_remote_list()
        layout.addWidget(QLabel("已安装的远程插件:"))
        layout.addWidget(self.remote_list)

        # 卸载按钮
        uninstall_btn = QPushButton("卸载选中插件")
        uninstall_btn.clicked.connect(self._on_uninstall_remote_plugin)
        layout.addWidget(uninstall_btn)

        return group

    def _on_install_remote_plugin(self) -> None:
        """处理安装远程插件"""
        url, ok = QInputDialog.getText(
            self,
            "安装远程插件",
            "请输入 GitHub raw URL:\n(例如: https://raw.githubusercontent.com/user/repo/main/plugin.py)"
        )

        if not ok or not url:
            return

        # 显示进度对话框
        progress = QProgressDialog("正在下载插件...", "取消", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        try:
            success, message = self.remote_manager.install_from_url(url)
            progress.close()

            if success:
                QMessageBox.information(self, "成功", message)
                self._refresh_remote_list()
                # 重新加载插件
                self.plugin_manager.load_plugins()
            else:
                QMessageBox.warning(self, "失败", message)
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "错误", f"安装失败: {str(e)}")

    def _refresh_remote_list(self) -> None:
        """刷新远程插件列表"""
        self.remote_list.clear()
        for plugin in self.remote_manager.list_installed():
            item = QListWidgetItem(
                f"{plugin['name']} ({plugin['plugin_type']}) - {plugin['install_date'][:10]}"
            )
            item.setData(Qt.UserRole, plugin['name'])
            self.remote_list.addItem(item)
```

#### 测试清单
- [ ] 从有效的 GitHub URL 安装插件
- [ ] 拒绝无效的 URL
- [ ] 拒绝不包含基类的代码
- [ ] 安装后插件能正常工作
- [ ] 重启应用后插件仍然存在
- [ ] 卸载功能正常工作

#### 已知限制
- ⚠️ 仅支持单文件插件
- ⚠️ 不验证代码安全性（用户需自行判断）
- ⚠️ 不检查依赖项
- ⚠️ 无版本管理

---

### v0.2 - 增强安全性和用户体验
**工作量**: 3-4 天
**目标**: 添加基础安全验证和更好的用户体验

#### 功能清单
- [x] 安全增强
  - [ ] SHA-256 校验和验证
  - [ ] 代码签名支持（可选，使用 GPG）
  - [ ] 插件白名单机制
  - [ ] 下载前预览插件信息
- [x] 用户体验改进
  - [ ] 显示插件详细信息（作者、描述、版本）
  - [ ] 安装前确认对话框
  - [ ] 进度反馈优化
  - [ ] 支持从剪贴板粘贴 URL
- [x] 元数据支持
  - [ ] 插件头部注释解析（docstring 格式）
  - [ ] 版本号提取

#### 前置条件（v0.2）
- MVP 功能已在 `feature/remote-plugins-mvp` 收敛，现阶段透过 Feature Flag 切换到 Beta 模式（例如 CLI `--enable-remote-plugins`）。
- `plugin_registry.json` schema 已版本化（如 `schema_version: 1`），以便在 v0.2 添加 checksum/metadata 字段。
- 发布前在至少 macOS + Windows 上验证 HTTPS 访问 GitHub raw 不受代理/证书问题影响。

#### 验收标准（v0.2）
- 安装流程提供 metadata 预览与 checksum 比对；若用户取消，系统不会写入任何档案。
- Registry 会记录 `version/author/checksum/dependencies`，并在 Settings UI 展示。
- 触发 `ruff check .` 与 `mypy ...plugins/` 不新增告警；新增的 metadata parser 有专属单元测试覆盖成功/失败路径。
- 至少一条 E2E 手动脚本（文档化）描述如何验证白名单与校验失败情形。

#### 迭代任务清单（v0.2）
- [x] Registry schema v2 migration/数据迁移脚本，确保老用户升级体验顺滑。
- [x] Metadata parser + checksum 计算模块上线，并复用至 `scripts/generate_index.py`。
- [x] Settings UI 新增 metadata 预览弹窗（Tk 版本）与白名单设置。
- [x] `PLUGIN_REPOSITORY_STRUCTURE` Phase 2：示例插件填写 metadata + 自动校验。

#### 插件元数据格式

```python
# 插件文件头部示例
"""
Universal Manga Downloader Plugin

Name: Example Site Parser
Author: Your Name
Version: 1.0.0
Description: Parser for example.com manga chapters
Repository: https://github.com/user/repo
License: MIT
Dependencies: requests>=2.28.0, lxml>=4.9.0
"""

from __future__ import annotations
from plugins.base import BasePlugin, ParsedChapter

class ExampleParser(BasePlugin):
    # 实现...
    pass
```

#### 元数据解析器

```python
# plugins/metadata_parser.py (新文件)
import re
from typing import TypedDict

class PluginMetadata(TypedDict, total=False):
    """插件元数据"""
    name: str
    author: str
    version: str
    description: str
    repository: str
    license: str
    dependencies: list[str]
    checksum: str  # SHA-256


def parse_plugin_metadata(code: str) -> PluginMetadata:
    """从插件代码中提取元数据"""
    metadata: PluginMetadata = {}

    # 提取 docstring（文件头部的三引号注释）
    docstring_match = re.search(r'^"""(.*?)"""', code, re.DOTALL | re.MULTILINE)
    if not docstring_match:
        return metadata

    docstring = docstring_match.group(1)

    # 解析各个字段
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

    # 解析依赖项（可能多行）
    deps_match = re.search(r"Dependencies:\s*(.+?)(?:\n\n|\Z)", docstring, re.DOTALL)
    if deps_match:
        deps_str = deps_match.group(1).strip()
        # 按逗号或换行分割
        deps = [d.strip() for d in re.split(r"[,\n]", deps_str) if d.strip()]
        metadata["dependencies"] = deps

    return metadata


def calculate_checksum(code: str) -> str:
    """计算代码的 SHA-256 校验和"""
    import hashlib
    return hashlib.sha256(code.encode()).hexdigest()
```

#### 增强的安装流程

```python
# plugins/remote_manager.py 更新
class RemotePluginManager:
    def install_from_url(
        self,
        url: str,
        expected_checksum: str | None = None
    ) -> tuple[bool, str]:
        """
        从 GitHub raw URL 安装插件（增强版）

        Args:
            url: GitHub raw URL
            expected_checksum: 可选的 SHA-256 校验和
        """
        try:
            # 下载内容
            with urlopen(url, timeout=30) as response:
                content = response.read().decode("utf-8")

            # 校验和验证（如果提供）
            if expected_checksum:
                actual_checksum = calculate_checksum(content)
                if actual_checksum != expected_checksum:
                    return False, f"校验和不匹配！期望: {expected_checksum[:16]}..., 实际: {actual_checksum[:16]}..."

            # 解析元数据
            metadata = parse_plugin_metadata(content)

            # 检查依赖
            if metadata.get("dependencies"):
                # 在 v0.2 只提示，不强制安装
                deps_str = ", ".join(metadata["dependencies"])
                logger.warning("Plugin requires dependencies: %s", deps_str)

            # 验证代码
            validation_result = self._validate_plugin_code(content)
            if not validation_result["valid"]:
                return False, f"插件验证失败: {validation_result['reason']}"

            # ... 保存文件和记录（与 v0.1 相同）

            # 更新注册表，包含元数据
            self.registry.append({
                "name": metadata.get("name", validation_result["plugin_name"]),
                "source_url": url,
                "install_date": datetime.now().isoformat(),
                "file_path": str(file_path),
                "plugin_type": validation_result["plugin_type"],
                "version": metadata.get("version", "unknown"),
                "author": metadata.get("author", "unknown"),
                "description": metadata.get("description", ""),
                "dependencies": metadata.get("dependencies", []),
                "checksum": calculate_checksum(content)
            })
            self._save_registry()

            return True, f"成功安装插件: {metadata.get('name', 'Unknown')}"

        except Exception as e:
            return False, f"安装失败: {str(e)}"
```

#### UI 改进 - 安装预览对话框

```python
# ui/dialogs/plugin_preview_dialog.py (新文件)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QDialogButtonBox
)

class PluginPreviewDialog(QDialog):
    """插件安装预览对话框"""

    def __init__(self, metadata: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插件信息预览")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # 显示元数据
        info_text = f"""
<h3>{metadata.get('name', 'Unknown Plugin')}</h3>
<p><b>版本:</b> {metadata.get('version', 'unknown')}</p>
<p><b>作者:</b> {metadata.get('author', 'unknown')}</p>
<p><b>描述:</b> {metadata.get('description', '无描述')}</p>
<p><b>类型:</b> {metadata.get('plugin_type', 'unknown')}</p>
"""

        if metadata.get('dependencies'):
            deps = '<br>'.join(f"  • {d}" for d in metadata['dependencies'])
            info_text += f"<p><b>依赖项:</b><br>{deps}</p>"
        else:
            info_text += "<p><b>依赖项:</b> 无</p>"

        info_text += f"""
<p><b>来源:</b> <a href="{metadata.get('source_url', '')}">{metadata.get('source_url', '')}</a></p>
<p><b>SHA-256:</b> <code>{metadata.get('checksum', '')[:32]}...</code></p>
"""

        info_label = QLabel(info_text)
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 警告信息
        warning = QLabel(
            "⚠️ <b>安全提示:</b> 请确保您信任此插件的来源。"
            "恶意插件可能包含有害代码。"
        )
        warning.setStyleSheet("color: orange; padding: 10px; background: #2b2b2b; border-radius: 5px;")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
```

#### 测试清单
- [ ] 元数据正确解析
- [ ] 校验和验证工作
- [ ] 依赖项检测并提示
- [ ] 预览对话框显示完整信息
- [ ] 用户可以取消安装

---

### v0.3 - 版本管理和更新
**工作量**: 4-5 天
**目标**: 实现完整的版本控制和自动更新检测

#### 功能清单
- [x] 版本管理
  - [x] 语义化版本比较（使用 `packaging` 库）
  - [x] 检查插件更新（对比远程版本）
  - [x] 一键更新到最新版本
  - [x] 回滚到旧版本（保留历史版本快照 + GUI/CLI 回滚）
- [x] 更新通知
  - [ ] 启动时自动检查更新
  - [x] 设置页面显示更新提示/可视反馈
  - [x] 批量更新所有插件（CLI `umd plugins update --all` 支援）
- [x] 版本历史
  - [x] 保存每个版本的元数据
  - [ ] 查看更新日志（如果提供）

#### 前置条件（v0.3）
- v0.2 metadata 已稳定并在 Registry 加入 `schema_version: 2`，确保可以持久化版本历史。
- 远端插件安装流程已可由 CLI 触发，以简化自动化测试更新流程。
- CI 中新增 smoke test，模拟将旧版插件更新成新版本并验证 `PluginManager.load_plugins()` 不重复实例化。

#### 验收标准（v0.3）
- 版本比较逻辑支援语义化与 fallback（未知版本视为 `0.0.0`），并在 `tests/test_plugins/test_version_manager.py` 取得 >=90% 覆盖率。
- Settings 或 CLI 可列出待更新插件，执行「更新」后会卸载旧版本并记录历史版本路径。
- 更新失败可在不中断 UI 的情况下回滚至旧版本，且相关日志含明确错误吗?
- 文档提供发布检查清单，指导如何在 `v1.3.6` 二进制中开启远端更新功能。

#### 迭代任务清单（v0.3）
- [x] `VersionManager` + 更新流程完成，registry 保存每个版本的 metadata/checksum。
- [x] Settings UI 提供检查/更新按钮与更新提示。
- [x] Remote manager 支援 inplace update、白名单检查、元数据预览复用。
- [x] `PLUGIN_REPOSITORY_STRUCTURE` Phase 3：index/网站显示版本、更新时间与校验和。
- [x] CLI `umd plugins …` 子命令：list/install/uninstall/check/update/history/rollback 全流程覆盖。

#### 版本比较实现

```python
# plugins/version_manager.py (新文件)
from __future__ import annotations

import logging
from packaging import version
from typing import TypedDict

logger = logging.getLogger(__name__)


class VersionInfo(TypedDict):
    """版本信息"""
    current: str
    latest: str
    has_update: bool
    changelog: str | None


class VersionManager:
    """插件版本管理器"""

    @staticmethod
    def compare_versions(current: str, latest: str) -> int:
        """
        比较版本号

        Returns:
            1 if latest > current
            0 if latest == current
            -1 if latest < current
        """
        try:
            v_current = version.parse(current)
            v_latest = version.parse(latest)

            if v_latest > v_current:
                return 1
            elif v_latest == v_current:
                return 0
            else:
                return -1
        except Exception as e:
            logger.error("Failed to compare versions: %s", e)
            return 0

    @staticmethod
    def fetch_latest_version(source_url: str) -> tuple[str | None, str | None]:
        """
        从源 URL 获取最新版本信息

        Returns:
            (version, content) 元组，失败返回 (None, None)
        """
        try:
            from urllib.request import urlopen

            with urlopen(source_url, timeout=10) as response:
                content = response.read().decode("utf-8")

            from plugins.metadata_parser import parse_plugin_metadata
            metadata = parse_plugin_metadata(content)

            return metadata.get("version"), content
        except Exception as e:
            logger.error("Failed to fetch latest version: %s", e)
            return None, None

    @staticmethod
    def check_for_updates(
        current_version: str,
        source_url: str
    ) -> VersionInfo:
        """检查是否有更新"""
        latest_version, _ = VersionManager.fetch_latest_version(source_url)

        if not latest_version:
            return VersionInfo(
                current=current_version,
                latest=current_version,
                has_update=False,
                changelog=None
            )

        has_update = VersionManager.compare_versions(
            current_version,
            latest_version
        ) > 0

        return VersionInfo(
            current=current_version,
            latest=latest_version,
            has_update=has_update,
            changelog=None  # v0.3 不实现 changelog 解析
        )


class UpdateManager:
    """管理插件更新"""

    def __init__(self, remote_manager):
        self.remote_manager = remote_manager

    def check_all_updates(self) -> dict[str, VersionInfo]:
        """检查所有远程插件的更新"""
        updates = {}

        for plugin in self.remote_manager.list_installed():
            name = plugin["name"]
            current_version = plugin.get("version", "unknown")
            source_url = plugin["source_url"]

            if current_version == "unknown":
                continue

            version_info = VersionManager.check_for_updates(
                current_version,
                source_url
            )

            if version_info["has_update"]:
                updates[name] = version_info

        return updates

    def update_plugin(self, plugin_name: str) -> tuple[bool, str]:
        """更新指定插件到最新版本"""
        # 查找插件记录
        plugin_record = None
        for record in self.remote_manager.registry:
            if record["name"] == plugin_name:
                plugin_record = record
                break

        if not plugin_record:
            return False, f"未找到插件: {plugin_name}"

        # 备份当前版本
        current_version = plugin_record.get("version", "unknown")
        source_url = plugin_record["source_url"]

        try:
            # 下载最新版本
            latest_version, content = VersionManager.fetch_latest_version(source_url)

            if not content:
                return False, "无法获取最新版本"

            # 卸载旧版本
            success, msg = self.remote_manager.uninstall(plugin_name)
            if not success:
                return False, f"卸载旧版本失败: {msg}"

            # 安装新版本
            success, msg = self.remote_manager.install_from_url(source_url)
            if not success:
                return False, f"安装新版本失败: {msg}"

            return True, f"成功更新 {plugin_name}: {current_version} → {latest_version}"

        except Exception as e:
            return False, f"更新失败: {str(e)}"
```

#### UI 更新 - 更新检查界面

```python
# ui/tabs/settings_tab.py 新增
class SettingsTab:
    def _create_update_section(self, parent: QWidget) -> QGroupBox:
        """创建更新检查区域"""
        group = QGroupBox("插件更新", parent)
        layout = QVBoxLayout(group)

        # 检查更新按钮
        check_btn = QPushButton("检查所有插件更新")
        check_btn.clicked.connect(self._on_check_updates)
        layout.addWidget(check_btn)

        # 更新列表
        self.update_list = QListWidget()
        layout.addWidget(QLabel("可用更新:"))
        layout.addWidget(self.update_list)

        # 更新按钮
        update_btn = QPushButton("更新选中插件")
        update_btn.clicked.connect(self._on_update_selected)
        layout.addWidget(update_btn)

        update_all_btn = QPushButton("更新全部")
        update_all_btn.clicked.connect(self._on_update_all)
        layout.addWidget(update_all_btn)

        return group

    def _on_check_updates(self) -> None:
        """检查更新"""
        progress = QProgressDialog("正在检查更新...", "取消", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        try:
            updates = self.update_manager.check_all_updates()
            progress.close()

            self.update_list.clear()

            if not updates:
                QMessageBox.information(self, "无更新", "所有插件均为最新版本")
                return

            for name, info in updates.items():
                item = QListWidgetItem(
                    f"{name}: {info['current']} → {info['latest']}"
                )
                item.setData(Qt.UserRole, name)
                self.update_list.addItem(item)

            QMessageBox.information(
                self,
                "发现更新",
                f"发现 {len(updates)} 个插件更新"
            )

        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "错误", f"检查更新失败: {str(e)}")

    def _on_update_selected(self) -> None:
        """更新选中的插件"""
        selected = self.update_list.currentItem()
        if not selected:
            return

        plugin_name = selected.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "确认更新",
            f"确定要更新插件 {plugin_name} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        success, message = self.update_manager.update_plugin(plugin_name)

        if success:
            QMessageBox.information(self, "成功", message)
            self._on_check_updates()  # 刷新列表
            self.plugin_manager.load_plugins()  # 重新加载插件
        else:
            QMessageBox.warning(self, "失败", message)
```

#### 测试清单
- [x] 版本比较正确（包括语义化版本）
- [x] 检测到可用更新
- [x] 更新成功且功能正常
- [x] 更新失败时能正确回滚（`tests/test_plugins/test_remote_manager.py::test_history_and_rollback`）
- [x] 批量更新工作正常（CLI --all 覆盖）

---

### v0.4 - 插件仓库和浏览
**工作量**: 5-7 天
**目标**: 建立社区插件仓库，支持可视化浏览和搜索

#### 功能清单
- [x] 插件仓库
  - [x] 设计仓库索引格式（JSON）
  - [x] 创建官方插件仓库（GitHub repo）
  - [x] 自动同步仓库索引（RepositoryManager + 缓存）
  - [x] 支持多个仓库源（Settings → Repositories 列表 + CLI 配置文件）
- [x] 浏览和搜索
  - [x] 插件市场 UI（Tk 列表视图 + 预览安装）
  - [x] 按类型筛选（Parser/Converter）
  - [x] 关键词搜索
  - [x] 排序（名称、下载量、更新日期）
- [x] 社区功能
  - [ ] 插件评分和评论（可选）
  - [ ] 下载统计
  - [ ] 提交插件的指南

#### 前置条件（v0.4）
- 官方 `umd-plugins/official` 仓库完成 CI（校验 checksum、lint 插件）并具备最少 3 个示例插件。
- 应用层面提供「只读模式」：即便仓库同步失败，仍可使用本地/已安装插件。
- v0.3 更新机制已经 GA，可确保市场安装的插件能自动接收后续更新。

#### 验收标准（v0.4）
- 仓库同步后，可在 UI 中分页显示 >=50 个插件并支持搜索/筛选，不造成 UI 卡顿（FPS > 40）。
- 至少一个 end-to-end 测试脚本涵盖「仓库同步 → 安装 → 卸载 → 重装」。
- 官方仓库文档 `PLUGIN_SUBMISSION.md` 发布，CI 针对 PR 自动运行验证脚本。
- Settings 中可切换仓库或新增自定义仓库 URL，并将此设定持久化在用户配置中。

#### 迭代任务清单（v0.4）
- [x] `PluginMarketTab`（Tk 版本）完成，加载 `RepositoryManager` 缓存。
- [x] `sync_repositories` 后台任务整合 QueueManager，避免阻塞 UI。
- [ ] GitHub Pages 市集上线（参考 `PLUGIN_REPOSITORY_STRUCTURE` Phase 3），包含搜索/筛选。
- [ ] 指南/issue template/pipeline 文档齐备（README + Submission Guide + issue templates）。

#### 仓库索引格式

```json
{
  "version": "1.0",
  "last_updated": "2025-01-15T12:00:00Z",
  "plugins": [
    {
      "id": "mangadex-enhanced",
      "name": "MangaDex Enhanced Parser",
      "type": "parser",
      "author": "community-dev",
      "version": "2.0.0",
      "description": "增强版 MangaDex 解析器，支持多语言和高级筛选",
      "source_url": "https://raw.githubusercontent.com/umd-plugins/official/main/parsers/mangadex_enhanced.py",
      "repository": "https://github.com/umd-plugins/official",
      "license": "MIT",
      "tags": ["mangadex", "enhanced", "multilang"],
      "dependencies": ["requests>=2.28.0"],
      "checksum": "sha256:abc123...",
      "downloads": 1234,
      "rating": 4.8,
      "screenshots": [
        "https://example.com/screenshot1.png"
      ],
      "created_at": "2024-06-01T00:00:00Z",
      "updated_at": "2025-01-10T00:00:00Z"
    },
    {
      "id": "epub-converter",
      "name": "EPUB Converter",
      "type": "converter",
      "author": "ebook-lover",
      "version": "1.5.0",
      "description": "将章节转换为 EPUB 电子书格式",
      "source_url": "https://raw.githubusercontent.com/umd-plugins/official/main/converters/epub_converter.py",
      "repository": "https://github.com/umd-plugins/official",
      "license": "MIT",
      "tags": ["epub", "ebook", "converter"],
      "dependencies": ["ebooklib>=0.18"],
      "checksum": "sha256:def456...",
      "downloads": 856,
      "rating": 4.6,
      "created_at": "2024-08-15T00:00:00Z",
      "updated_at": "2024-12-20T00:00:00Z"
    }
  ]
}
```

#### 仓库管理器

```python
# plugins/repository_manager.py (新文件)
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from urllib.request import urlopen

logger = logging.getLogger(__name__)

PluginType = Literal["parser", "converter"]


@dataclass
class PluginEntry:
    """仓库中的插件条目"""
    id: str
    name: str
    type: PluginType
    author: str
    version: str
    description: str
    source_url: str
    repository: str
    license: str
    tags: list[str]
    dependencies: list[str]
    checksum: str
    downloads: int
    rating: float
    created_at: str
    updated_at: str
    screenshots: list[str] | None = None


class RepositoryManager:
    """管理插件仓库"""

    DEFAULT_REPO_URL = "https://raw.githubusercontent.com/umd-plugins/official/main/index.json"

    def __init__(self):
        self.repositories: list[str] = [self.DEFAULT_REPO_URL]
        self.cache: list[PluginEntry] = []
        self.last_sync: datetime | None = None

    def add_repository(self, url: str) -> None:
        """添加自定义仓库源"""
        if url not in self.repositories:
            self.repositories.append(url)

    def sync(self) -> tuple[bool, str]:
        """同步所有仓库索引"""
        all_plugins = []

        for repo_url in self.repositories:
            try:
                logger.info("Syncing repository: %s", repo_url)
                with urlopen(repo_url, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))

                for plugin_data in data.get("plugins", []):
                    try:
                        plugin = PluginEntry(**plugin_data)
                        all_plugins.append(plugin)
                    except Exception as e:
                        logger.error("Failed to parse plugin entry: %s", e)

            except Exception as e:
                logger.error("Failed to sync repository %s: %s", repo_url, e)

        if not all_plugins:
            return False, "无法同步任何仓库"

        self.cache = all_plugins
        self.last_sync = datetime.now()
        return True, f"成功同步 {len(all_plugins)} 个插件"

    def search(
        self,
        query: str = "",
        plugin_type: PluginType | None = None,
        tags: list[str] | None = None
    ) -> list[PluginEntry]:
        """搜索插件"""
        results = self.cache.copy()

        # 类型筛选
        if plugin_type:
            results = [p for p in results if p.type == plugin_type]

        # 标签筛选
        if tags:
            results = [
                p for p in results
                if any(tag in p.tags for tag in tags)
            ]

        # 关键词搜索
        if query:
            query_lower = query.lower()
            results = [
                p for p in results
                if query_lower in p.name.lower()
                or query_lower in p.description.lower()
                or query_lower in p.author.lower()
            ]

        return results

    def get_by_id(self, plugin_id: str) -> PluginEntry | None:
        """根据 ID 获取插件"""
        for plugin in self.cache:
            if plugin.id == plugin_id:
                return plugin
        return None

    def sort_by(
        self,
        plugins: list[PluginEntry],
        key: Literal["name", "downloads", "rating", "updated_at"]
    ) -> list[PluginEntry]:
        """排序插件列表"""
        if key == "name":
            return sorted(plugins, key=lambda p: p.name.lower())
        elif key == "downloads":
            return sorted(plugins, key=lambda p: p.downloads, reverse=True)
        elif key == "rating":
            return sorted(plugins, key=lambda p: p.rating, reverse=True)
        elif key == "updated_at":
            return sorted(plugins, key=lambda p: p.updated_at, reverse=True)
        return plugins
```

#### 插件市场 UI

```python
# ui/tabs/plugin_market_tab.py (新文件)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QComboBox, QScrollArea, QLabel,
    QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class SyncThread(QThread):
    """后台同步线程"""
    finished = pyqtSignal(bool, str)

    def __init__(self, repo_manager):
        super().__init__()
        self.repo_manager = repo_manager

    def run(self):
        success, message = self.repo_manager.sync()
        self.finished.emit(success, message)


class PluginCard(QFrame):
    """插件卡片组件"""

    def __init__(self, plugin: PluginEntry, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            PluginCard {
                background: #2b2b2b;
                border: 1px solid #3b3b3b;
                border-radius: 8px;
                padding: 12px;
            }
            PluginCard:hover {
                border-color: #4b4b4b;
            }
        """)

        layout = QVBoxLayout(self)

        # 标题行
        title_layout = QHBoxLayout()
        name_label = QLabel(f"<b>{self.plugin.name}</b>")
        title_layout.addWidget(name_label)

        type_badge = QLabel(self.plugin.type.upper())
        type_badge.setStyleSheet(
            "background: #007acc; color: white; "
            "padding: 2px 8px; border-radius: 3px;"
        )
        title_layout.addWidget(type_badge)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # 描述
        desc_label = QLabel(self.plugin.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #999;")
        layout.addWidget(desc_label)

        # 元信息
        meta_text = f"作者: {self.plugin.author} | 版本: {self.plugin.version} | 下载: {self.plugin.downloads}"
        meta_label = QLabel(meta_text)
        meta_label.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(meta_label)

        # 安装按钮
        install_btn = QPushButton("安装")
        install_btn.clicked.connect(self._on_install)
        layout.addWidget(install_btn)

    def _on_install(self):
        # 触发父组件的安装逻辑
        self.parent().parent().parent().parent().install_plugin(self.plugin)


class PluginMarketTab(QWidget):
    """插件市场标签页"""

    def __init__(self, repo_manager, remote_manager, parent=None):
        super().__init__(parent)
        self.repo_manager = repo_manager
        self.remote_manager = remote_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 顶部工具栏
        toolbar = QHBoxLayout()

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索插件...")
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)

        # 类型筛选
        self.type_filter = QComboBox()
        self.type_filter.addItems(["全部", "解析器", "转换器"])
        self.type_filter.currentTextChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.type_filter)

        # 排序
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["名称", "下载量", "评分", "更新时间"])
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        toolbar.addWidget(self.sort_combo)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._on_refresh)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # 插件列表（可滚动）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.plugin_container = QWidget()
        self.plugin_layout = QVBoxLayout(self.plugin_container)
        self.plugin_layout.addStretch()

        scroll_area.setWidget(self.plugin_container)
        layout.addWidget(scroll_area)

        # 初始同步
        self._on_refresh()

    def _on_refresh(self):
        """刷新插件列表"""
        self.sync_thread = SyncThread(self.repo_manager)
        self.sync_thread.finished.connect(self._on_sync_finished)
        self.sync_thread.start()

    def _on_sync_finished(self, success: bool, message: str):
        """同步完成"""
        if success:
            self._update_plugin_list()
        else:
            QMessageBox.warning(self, "同步失败", message)

    def _update_plugin_list(self):
        """更新插件列表显示"""
        # 清空现有卡片
        while self.plugin_layout.count() > 1:  # 保留最后的 stretch
            item = self.plugin_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 应用筛选和排序
        plugins = self._get_filtered_plugins()

        # 创建卡片
        for plugin in plugins:
            card = PluginCard(plugin)
            self.plugin_layout.insertWidget(self.plugin_layout.count() - 1, card)

    def _get_filtered_plugins(self) -> list[PluginEntry]:
        """获取筛选后的插件列表"""
        # 类型筛选
        type_map = {"全部": None, "解析器": "parser", "转换器": "converter"}
        plugin_type = type_map[self.type_filter.currentText()]

        # 搜索
        query = self.search_input.text()

        plugins = self.repo_manager.search(query, plugin_type)

        # 排序
        sort_map = {"名称": "name", "下载量": "downloads", "评分": "rating", "更新时间": "updated_at"}
        sort_key = sort_map[self.sort_combo.currentText()]

        return self.repo_manager.sort_by(plugins, sort_key)

    def _on_search(self):
        """搜索文本变化"""
        self._update_plugin_list()

    def _on_filter_changed(self):
        """筛选条件变化"""
        self._update_plugin_list()

    def _on_sort_changed(self):
        """排序方式变化"""
        self._update_plugin_list()

    def install_plugin(self, plugin: PluginEntry):
        """安装插件"""
        reply = QMessageBox.question(
            self,
            "确认安装",
            f"确定要安装 {plugin.name} v{plugin.version} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 使用远程管理器安装（带校验和验证）
        success, message = self.remote_manager.install_from_url(
            plugin.source_url,
            expected_checksum=plugin.checksum.replace("sha256:", "")
        )

        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "失败", message)
```

#### 集成到主应用

```python
# ui/app.py 更新
from plugins.repository_manager import RepositoryManager
from ui.tabs.plugin_market_tab import PluginMarketTab

class App(QMainWindow):
    def _create_tabs(self):
        # ... 现有标签页

        # 新增插件市场标签页
        self.repo_manager = RepositoryManager()
        market_tab = PluginMarketTab(
            self.repo_manager,
            self.remote_manager,
            self
        )
        self.tabs.addTab(market_tab, "插件市场")
```

#### 插件提交指南

创建 `PLUGIN_SUBMISSION.md` 文档：

```markdown
# 插件提交指南

## 准备工作

1. 确保你的插件符合以下要求：
   - 单个 `.py` 文件
   - 继承 `BasePlugin` 或 `BaseConverter`
   - 包含完整的元数据注释
   - 通过基础测试

2. 插件元数据示例：

```python
"""
Universal Manga Downloader Plugin

Name: My Awesome Parser
Author: Your Name
Version: 1.0.0
Description: Parser for awesome-manga.com
Repository: https://github.com/yourname/your-plugin-repo
License: MIT
Dependencies: requests>=2.28.0
"""
```

## 提交流程

1. Fork 官方插件仓库: https://github.com/umd-plugins/official
2. 将你的插件放到相应目录:
   - 解析器: `parsers/your_plugin.py`
   - 转换器: `converters/your_plugin.py`
3. 运行验证脚本: `python scripts/validate_plugin.py parsers/your_plugin.py`
4. 提交 Pull Request，标题格式: `[Plugin] Add YourPluginName`
5. 在 PR 描述中包含:
   - 插件功能说明
   - 测试截图
   - 依赖项说明

## 审核标准

- ✅ 代码质量（类型提示、错误处理）
- ✅ 安全性（无恶意代码、无敏感信息泄露）
- ✅ 功能性（能正常工作）
- ✅ 文档完整性（元数据齐全）

审核通过后，你的插件将出现在插件市场！
```

#### 测试清单
- [ ] 仓库索引正确同步
- [ ] 搜索和筛选工作正常
- [ ] 插件卡片显示完整信息
- [ ] 从市场安装插件成功
- [ ] 校验和验证工作

---

### v0.5 - 依赖管理和多文件支持
**工作量**: 5-6 天
**目标**: 自动处理插件依赖，支持复杂的多文件插件

#### 功能清单
- [x] 依赖管理
  - [ ] 自动检测缺失的依赖包
  - [ ] 一键安装依赖（使用 pip）
  - [ ] 虚拟环境隔离（可选）
  - [ ] 依赖冲突检测
- [x] 多文件插件
  - [ ] 支持插件包（文件夹）
  - [ ] ZIP 包下载和解压
  - [ ] `__init__.py` 入口点支持
  - [ ] 资源文件处理（配置、图片等）
- [x] 高级功能
  - [ ] 插件配置界面（每个插件可定义设置）
  - [ ] 插件间通信（事件系统）

#### 前置条件（v0.5）
- 官方文档已定义「受信任插件」指南，并在 Registry 中加注 `requires_dependencies: bool`。
- CI/CD 管线可触发隔离环境（virtualenv 或 container）来执行外部依赖安装，避免污染主开发环境。
- ZIP/多文件插件规范（入口点、资源路径）经 architecture review 批准。

#### 验收标准（v0.5）
- Dependency Manager 可辨识缺失依赖并提供一键安装；若安装失败，系统会回退所有文件并提示用户。
- 多文件插件透过 ZIP 安装时，`PluginManager` 仍能列出其 Parser/Converter 类别，且 `pytest tests/test_plugins -k multi_file` 通过。
- 高级插件设置可在 Settings UI 中显示/编辑，并通过 `config.py` 持久化。
- 事件系统文档化至少两个示例场景（如下载前后钩子），并提供最少一个示例插件验证通信流程。

#### 迭代任务清单（v0.5）
- [ ] Dependency Manager + CLI `umd plugins --install-deps`，与 GUI dialog 共享实现。
- [ ] ZIP / 多文件插件安装流程（含解压、入口验证、签名校验）。
- [ ] 插件配置/事件总线 API（文档 + 示例插件 + tests）。
- [ ] `PLUGIN_REPOSITORY_STRUCTURE` Phase 4：在仓库中标识多文件插件、依赖声明与信任等级。

#### 依赖安装器

```python
# plugins/dependency_manager.py (新文件)
from __future__ import annotations

import subprocess
import sys
import logging
from typing import TypedDict

logger = logging.getLogger(__name__)


class DependencyInfo(TypedDict):
    """依赖信息"""
    package: str
    version_spec: str
    installed: bool
    installed_version: str | None


class DependencyManager:
    """管理插件依赖"""

    @staticmethod
    def check_dependencies(requirements: list[str]) -> list[DependencyInfo]:
        """
        检查依赖是否已安装

        Args:
            requirements: 格式如 ["requests>=2.28.0", "lxml"]
        """
        import importlib.metadata

        results = []

        for req in requirements:
            # 解析包名和版本要求
            if ">=" in req:
                package, version_spec = req.split(">=")
            elif "==" in req:
                package, version_spec = req.split("==")
            else:
                package = req
                version_spec = ""

            package = package.strip()
            version_spec = version_spec.strip()

            # 检查是否已安装
            try:
                installed_version = importlib.metadata.version(package)
                installed = True
            except importlib.metadata.PackageNotFoundError:
                installed_version = None
                installed = False

            results.append(DependencyInfo(
                package=package,
                version_spec=version_spec,
                installed=installed,
                installed_version=installed_version
            ))

        return results

    @staticmethod
    def install_dependencies(
        requirements: list[str],
        progress_callback=None
    ) -> tuple[bool, str]:
        """
        安装依赖包

        Args:
            requirements: 依赖列表
            progress_callback: 可选的进度回调函数
        """
        try:
            # 使用 pip 安装
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--user",  # 用户级安装，避免权限问题
                *requirements
            ]

            logger.info("Installing dependencies: %s", requirements)

            if progress_callback:
                progress_callback("正在安装依赖...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode == 0:
                return True, "依赖安装成功"
            else:
                return False, f"安装失败: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "安装超时"
        except Exception as e:
            logger.error("Failed to install dependencies: %s", e)
            return False, f"安装失败: {str(e)}"

    @staticmethod
    def detect_conflicts(
        new_requirements: list[str],
        existing_requirements: list[str]
    ) -> list[str]:
        """检测依赖冲突"""
        conflicts = []

        # 简化版：仅检查版本号冲突
        new_dict = {}
        for req in new_requirements:
            if "==" in req:
                package, version = req.split("==")
                new_dict[package.strip()] = version.strip()

        for req in existing_requirements:
            if "==" in req:
                package, version = req.split("==")
                package = package.strip()
                version = version.strip()

                if package in new_dict and new_dict[package] != version:
                    conflicts.append(
                        f"{package}: 需要 {new_dict[package]}, 已安装 {version}"
                    )

        return conflicts
```

#### 依赖安装 UI

```python
# ui/dialogs/dependency_dialog.py (新文件)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget,
    QProgressBar, QPushButton, QDialogButtonBox
)
from PyQt6.QtCore import QThread, pyqtSignal


class InstallThread(QThread):
    """依赖安装线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, requirements):
        super().__init__()
        self.requirements = requirements

    def run(self):
        from plugins.dependency_manager import DependencyManager

        self.progress.emit("正在安装依赖...")
        success, message = DependencyManager.install_dependencies(
            self.requirements,
            progress_callback=self.progress.emit
        )
        self.finished.emit(success, message)


class DependencyDialog(QDialog):
    """依赖安装对话框"""

    def __init__(self, dependencies: list[str], parent=None):
        super().__init__(parent)
        self.dependencies = dependencies
        self.setWindowTitle("安装依赖")
        self.setMinimumWidth(400)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 说明
        info_label = QLabel("此插件需要以下依赖包:")
        layout.addWidget(info_label)

        # 依赖列表
        from plugins.dependency_manager import DependencyManager
        dep_info = DependencyManager.check_dependencies(self.dependencies)

        self.dep_list = QListWidget()
        for dep in dep_info:
            status = "✓ 已安装" if dep["installed"] else "✗ 未安装"
            version = f" ({dep['installed_version']})" if dep["installed_version"] else ""
            text = f"{dep['package']}{version} - {status}"
            self.dep_list.addItem(text)

        layout.addWidget(self.dep_list)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定模式
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # 按钮
        self.buttons = QDialogButtonBox()

        # 检查是否有未安装的依赖
        missing = [d for d in dep_info if not d["installed"]]

        if missing:
            install_btn = QPushButton("安装全部")
            install_btn.clicked.connect(self._on_install)
            self.buttons.addButton(install_btn, QDialogButtonBox.ButtonRole.AcceptRole)

            skip_btn = QPushButton("跳过")
            skip_btn.clicked.connect(self.reject)
            self.buttons.addButton(skip_btn, QDialogButtonBox.ButtonRole.RejectRole)
        else:
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(self.accept)
            self.buttons.addButton(ok_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        layout.addWidget(self.buttons)

    def _on_install(self):
        """开始安装"""
        self.progress_bar.show()
        self.buttons.setEnabled(False)

        self.install_thread = InstallThread(self.dependencies)
        self.install_thread.progress.connect(self.status_label.setText)
        self.install_thread.finished.connect(self._on_install_finished)
        self.install_thread.start()

    def _on_install_finished(self, success: bool, message: str):
        """安装完成"""
        self.progress_bar.hide()
        self.buttons.setEnabled(True)
        self.status_label.setText(message)

        if success:
            self.accept()
```

#### 多文件插件支持

```python
# plugins/package_loader.py (新文件)
from __future__ import annotations

import zipfile
import tempfile
import shutil
from pathlib import Path


class PluginPackageLoader:
    """加载多文件插件包"""

    @staticmethod
    def install_package(zip_url: str, plugin_dir: Path) -> tuple[bool, str]:
        """
        从 ZIP URL 安装插件包

        结构示例:
        plugin_package.zip
        ├── __init__.py          # 入口点
        ├── parser.py            # 解析器实现
        ├── utils.py             # 工具函数
        └── config.json          # 配置文件
        """
        try:
            from urllib.request import urlopen

            # 下载 ZIP
            with urlopen(zip_url, timeout=30) as response:
                zip_data = response.read()

            # 解压到临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                zip_path = temp_path / "plugin.zip"
                zip_path.write_bytes(zip_data)

                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(temp_path / "extracted")

                extracted_path = temp_path / "extracted"

                # 验证结构
                init_file = extracted_path / "__init__.py"
                if not init_file.exists():
                    return False, "插件包缺少 __init__.py 入口文件"

                # 读取 __init__.py 获取包名
                init_content = init_file.read_text(encoding="utf-8")

                # 提取包名（假设有 __plugin_name__ 变量）
                import re
                match = re.search(r'__plugin_name__\s*=\s*["\'](.+?)["\']', init_content)
                if not match:
                    return False, "未找到 __plugin_name__ 定义"

                package_name = match.group(1)

                # 复制到插件目录
                target_dir = plugin_dir / package_name
                if target_dir.exists():
                    return False, f"插件包 {package_name} 已存在"

                shutil.copytree(extracted_path, target_dir)

                return True, f"成功安装插件包: {package_name}"

        except Exception as e:
            return False, f"安装失败: {str(e)}"
```

#### 测试清单
- [ ] 依赖检测正确
- [ ] 自动安装依赖成功
- [ ] 多文件插件能正常加载
- [ ] ZIP 包解压和安装工作
- [ ] 依赖冲突能被检测

---

## 里程碑依赖关系

| 阶段 | 必要前置 | 关键输出 | 备注 |
| --- | --- | --- | --- |
| v0.1 → v0.2 | Feature flag 管理、registry 基本 schema | 远端安装 MVP | 若 v0.1 未完成 schema versioning，会导致 v0.2 metadata 无法落地 |
| v0.2 → v0.3 | Metadata + checksum | 版本管理 & 更新 | 依赖 `version` 字段与 checksum 才能比较/回滚 |
| v0.3 → v0.4 | 更新机制 GA | 仓库同步与市场 | 市场安装后必须复用更新逻辑，否则用户会停留在旧版 |
| v0.4 → v0.5 | 仓库/安装流程稳定 | 依赖管理、多文件 | 市场需能区分单文件与多文件条目，并提供依赖提示 |

> 建议在每个阶段结束时发布一个带 Beta Feature Flag 的 `v1.3.6+x` 小版本，方便回收用户反馈并避免一次性堆积风险。

## 总体时间估算

| 版本 | 功能 | 工作量 | 累计时间 |
|------|------|--------|----------|
| v0.1 | MVP - 基础下载安装 | 3-5天 | 3-5天 |
| v0.2 | 安全性和元数据 | 3-4天 | 6-9天 |
| v0.3 | 版本管理和更新 | 4-5天 | 10-14天 |
| v0.4 | 插件仓库和市场 | 5-7天 | 15-21天 |
| v0.5 | 依赖管理和多文件 | 5-6天 | 20-27天 |

**总计**: 约 4-5 周全职开发时间

---

## 风险评估

### 高风险
1. **安全性**: 恶意代码执行（需要代码审核机制）
2. **依赖冲突**: pip 包版本冲突可能破坏环境

### 中风险
3. **下载失败**: 网络问题导致安装失败（需要重试机制）
4. **兼容性**: 不同 Python 版本的兼容性问题

### 低风险
5. **UI 性能**: 大量插件时界面卡顿（可通过分页解决）

---

## 实现建议

### 优先级排序
1. **必须实现**: v0.1 (MVP) - 核心功能
2. **应该实现**: v0.2 (安全性) + v0.3 (更新)
3. **可以实现**: v0.4 (市场)
4. **锦上添花**: v0.5 (高级功能)

### 技术栈选择
- **HTTP 请求**: `urllib.request` (标准库) 或 `requests`
- **版本比较**: `packaging` 库
- **依赖安装**: `pip` (subprocess)
- **UI**: PyQt6 (已使用)

### 测试策略
- 每个版本完成后进行完整测试
- 建立测试插件仓库用于验证
- 社区 Beta 测试收集反馈

### CI / 发布流程（针对 v1.3.6+）
1. **分支策略**：每个阶段使用专属 feature 分支（如 `feature/remote-plugins-v0.2`），并在合并前 rebase 自 `develop`（或当前主干）。
2. **自动化**：CI pipeline 新增三段：
   - `remote-plugin-lint`: 针对 `plugins/remote_*` 与 `services/` 新增代码执行 `ruff`/`mypy`。
   - `remote-plugin-e2e`: 以 pytest 标记 `@pytest.mark.remote_plugin` 的整合测试。
   - `artifact-scan`: 生成测试用 zip/raw 插件并计算 checksum，作为发布附件。
3. **签署与公告**：在 GitHub Release 草稿中标注 `Requires --enable-remote-plugins`，并附上 README 章节链接。
4. **回滚策略**：若发现远端插件导致崩溃，提供 CLI `--disable-remote-plugins` 与设置面板的紧急开关，同时在 registry 中保留最近已知良好版本的快照。

---

## 后续扩展方向

### v0.6+ 可能的功能
- 插件沙箱隔离（使用 Docker 或 VM）
- 插件性能分析工具
- 插件开发脚手架（CLI 工具）
- 插件热重载（无需重启应用）
- 云同步插件配置
- 插件评论和社区互动

---

## 结论

将插件系统改造为支持远程下载的功能是**中等复杂度**的项目：

- ✅ **基础实现简单**: v0.1 只需 3-5 天即可完成 MVP
- ⚠️ **完整实现需时**: 完整功能需要 4-5 周
- 🎯 **建议分阶段**: 先做 v0.1-v0.3，收集反馈后再决定是否实现 v0.4-v0.5

**推荐路线**:
1. 先用 1 周实现 v0.1 + v0.2，验证可行性
2. 再用 1 周实现 v0.3，形成基础完整版
3. 根据用户反馈决定是否投入 2-3 周实现市场和高级功能
