"""Settings tab UI components and event handlers."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from functools import partial
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING, cast

from config import CONFIG
from plugins.base import PluginType
from plugins.dependency_manager import DependencyManager
from ui.widgets import clamp_value
from utils.file_utils import get_default_download_root

if TYPE_CHECKING:
    from plugins.base import PluginManager
    from plugins.remote_manager import (
        PreparedRemotePlugin,
        RemotePluginHistoryEntry,
        RemotePluginManager,
        RemotePluginRecord,
    )
    from plugins.repository_manager import (
        PluginEntryType,
        PluginRepositoryEntry,
        RepositoryManager,
    )

logger = logging.getLogger(__name__)


class SettingsTabMixin:
    """Mixin providing Settings tab UI construction and event handlers."""

    # Type hints for attributes expected from host class
    plugin_manager: PluginManager
    remote_plugin_manager: RemotePluginManager
    repository_manager: RepositoryManager
    plugin_vars: dict[tuple[PluginType, str], tk.BooleanVar]
    chapter_workers_var: tk.IntVar
    image_workers_var: tk.IntVar
    download_dir_var: tk.StringVar
    download_dir_path: str
    _chapter_workers_value: int
    _image_workers_value: int
    download_dir_entry: ttk.Entry
    chapter_workers_spinbox: ttk.Spinbox
    image_workers_spinbox: ttk.Spinbox

    # Methods expected from host class
    def _set_status(self, message: str) -> None:  # type: ignore[empty-body]
        """Update status label."""
    def _refresh_provider_options(self) -> None:  # type: ignore[empty-body]
        """Refresh provider options."""
    def _ensure_chapter_executor(self, force_reset: bool = False) -> None:  # type: ignore[empty-body]
        """Ensure chapter executor is ready."""

    def _build_settings_tab(self, parent: ttk.Frame) -> None:
        """Construct the Settings tab UI within the given parent frame."""
        # --- Download Settings ---
        settings_frame = ttk.LabelFrame(parent, text="Download Settings")
        settings_frame.pack(fill="x", expand=False, padx=10, pady=(12, 10))

        # Directory selection
        directory_frame = ttk.Frame(settings_frame)
        directory_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(directory_frame, text="Save to:").pack(side="left")
        self.download_dir_entry = ttk.Entry(
            directory_frame, textvariable=self.download_dir_var
        )
        self.download_dir_entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(
            directory_frame, text="Browse…", command=self._browse_download_dir
        ).pack(side="left")

        # Concurrency settings
        concurrency_frame = ttk.Frame(settings_frame)
        concurrency_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(concurrency_frame, text="Chapter workers:").pack(side="left")
        self.chapter_workers_spinbox = ttk.Spinbox(
            concurrency_frame,
            from_=CONFIG.download.min_chapter_workers,
            to=CONFIG.download.max_chapter_workers,
            width=4,
            textvariable=self.chapter_workers_var,
            command=self._on_chapter_workers_change,
        )
        self.chapter_workers_spinbox.pack(side="left", padx=(6, 18))
        self.chapter_workers_spinbox.bind("<FocusOut>", self._on_chapter_workers_change)

        ttk.Label(concurrency_frame, text="Image workers:").pack(side="left")
        self.image_workers_spinbox = ttk.Spinbox(
            concurrency_frame,
            from_=CONFIG.download.min_image_workers,
            to=CONFIG.download.max_image_workers,
            width=4,
            textvariable=self.image_workers_var,
            command=self._on_image_workers_change,
        )
        self.image_workers_spinbox.pack(side="left", padx=(6, 0))
        self.image_workers_spinbox.bind("<FocusOut>", self._on_image_workers_change)

        # Plugin settings
        plugin_section_parent = ttk.Frame(parent)
        plugin_section_parent.pack(fill="both", expand=True, padx=10, pady=(0, 12))
        self._plugin_settings_parent = plugin_section_parent
        self._plugin_container: ttk.LabelFrame | None = None
        self._remote_plugin_frame: ttk.LabelFrame | None = None
        self._remote_plugins_tree: ttk.Treeview | None = None
        self._whitelist_listbox: tk.Listbox | None = None
        self._repository_listbox: tk.Listbox | None = None
        self.remote_plugin_url_var = tk.StringVar()
        self._whitelist_entry_var = tk.StringVar()
        self._repository_entry_var = tk.StringVar()
        self._pending_updates: set[str] = set()
        self._market_tree: ttk.Treeview | None = None
        self._market_entries: dict[str, PluginRepositoryEntry] = {}
        self._market_search_var = tk.StringVar()
        self._market_type_var = tk.StringVar(value="All")
        self._market_sort_var = tk.StringVar(value="name")
        self._build_plugin_settings(plugin_section_parent)
        self._build_remote_plugin_section(plugin_section_parent)
        self._build_plugin_market_section(plugin_section_parent)

    def _build_plugin_settings(self, parent: ttk.Frame) -> None:
        """Render plugin toggle controls within the settings tab."""
        self._plugin_settings_parent = parent
        existing_container = getattr(self, "_plugin_container", None)
        if existing_container is not None:
            existing_container.destroy()

        plugin_records = self.plugin_manager.get_records()
        if not plugin_records:
            return

        self._plugin_container = ttk.LabelFrame(parent, text="Plugins")
        self._plugin_container.pack(fill="both", expand=True, padx=0, pady=(0, 12))

        ttk.Label(
            self._plugin_container,
            text="Enable or disable plugins for this session. Changes apply immediately.",
            wraplength=420,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(8, 6))

        self.plugin_vars.clear()
        for plugin_type in PluginType:
            records = self.plugin_manager.get_records(plugin_type)
            if not records:
                continue

            section = ttk.LabelFrame(self._plugin_container, text=f"{plugin_type.value.title()} Plugins")
            section.pack(fill="x", expand=False, padx=10, pady=(0, 10))

            for record in records:
                name = record.name
                var = tk.BooleanVar(value=record.enabled)
                self.plugin_vars[(plugin_type, name)] = var
                ttk.Checkbutton(
                    section,
                    text=name,
                    variable=var,
                    command=partial(self._on_plugin_toggle, plugin_type, name),
                ).pack(anchor="w", padx=8, pady=2)

    def _build_remote_plugin_section(self, parent: ttk.Frame) -> None:
        existing_frame = getattr(self, "_remote_plugin_frame", None)
        if existing_frame is not None:
            existing_frame.destroy()

        frame = ttk.LabelFrame(parent, text="Remote Plugins (Beta)")
        frame.pack(fill="both", expand=True, padx=0, pady=(0, 12))
        self._remote_plugin_frame = frame

        description = (
            "Install parser/converter plugins from trusted GitHub raw URLs. "
            "Installed plugins are loaded immediately."
        )
        ttk.Label(frame, text=description, wraplength=420, justify="left").pack(
            anchor="w", padx=10, pady=(8, 6)
        )

        entry_row = ttk.Frame(frame)
        entry_row.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Label(entry_row, text="GitHub Raw URL:").pack(side="left")
        entry = ttk.Entry(entry_row, textvariable=self.remote_plugin_url_var)
        entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(entry_row, text="Install", command=self._install_remote_plugin).pack(side="left")

        whitelist_frame = ttk.LabelFrame(frame, text="Allowed Sources")
        whitelist_frame.pack(fill="x", padx=10, pady=(0, 8))
        listbox = tk.Listbox(whitelist_frame, height=4)
        listbox.pack(fill="x", padx=4, pady=4)
        self._whitelist_listbox = listbox

        whitelist_controls = ttk.Frame(whitelist_frame)
        whitelist_controls.pack(fill="x", padx=4, pady=(0, 4))
        entry = ttk.Entry(whitelist_controls, textvariable=self._whitelist_entry_var)
        entry.pack(side="left", fill="x", expand=True)
        ttk.Button(
            whitelist_controls,
            text="Add",
            command=self._add_allowed_source,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            whitelist_controls,
            text="Remove",
            command=self._remove_allowed_source,
        ).pack(side="left", padx=(6, 0))

        tree = ttk.Treeview(frame, columns=("name", "type", "version", "source"), show="headings", height=6)
        tree.heading("name", text="Plugin")
        tree.heading("type", text="Type")
        tree.heading("version", text="Version")
        tree.heading("source", text="Source URL")
        tree.column("name", width=160, anchor="w")
        tree.column("type", width=70, anchor="center")
        tree.column("version", width=80, anchor="center")
        tree.column("source", width=260, anchor="w")
        tree.pack(fill="both", expand=True, padx=10, pady=4)
        self._remote_plugins_tree = tree

        action_row = ttk.Frame(frame)
        action_row.pack(fill="x", padx=10, pady=(4, 10))
        ttk.Button(action_row, text="Uninstall Selected", command=self._uninstall_remote_plugin).pack(
            side="left"
        )
        ttk.Button(action_row, text="Refresh", command=self._refresh_remote_plugin_list).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(action_row, text="Check Updates", command=self._check_remote_updates).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(action_row, text="Update Selected", command=self._update_remote_plugin).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(action_row, text="History / Rollback", command=self._show_remote_plugin_history).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(action_row, text="Check Dependencies", command=self._check_remote_dependencies).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(action_row, text="Install Missing Deps", command=self._install_remote_dependencies).pack(
            side="left", padx=(6, 0)
        )

        self._refresh_remote_plugin_list()
        self._refresh_whitelist_ui()

    def _build_plugin_market_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Plugin Market (Preview)")
        frame.pack(fill="both", expand=True, padx=0, pady=(0, 0))

        controls = ttk.Frame(frame)
        controls.pack(fill="x", padx=10, pady=(8, 4))

        ttk.Label(controls, text="Search:").pack(side="left")
        search_entry = ttk.Entry(controls, textvariable=self._market_search_var, width=24)
        search_entry.pack(side="left", padx=(6, 12))
        self._market_search_var.trace_add("write", lambda *_: self._refresh_market_tree())

        ttk.Label(controls, text="Type:").pack(side="left")
        type_combo = ttk.Combobox(
            controls,
            state="readonly",
            values=["All", "parser", "converter"],
            textvariable=self._market_type_var,
            width=10,
        )
        type_combo.pack(side="left", padx=(6, 12))
        type_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_market_tree())

        ttk.Label(controls, text="Sort:").pack(side="left")
        sort_combo = ttk.Combobox(
            controls,
            state="readonly",
            values=["name", "downloads", "rating", "updated_at"],
            textvariable=self._market_sort_var,
            width=12,
        )
        sort_combo.pack(side="left", padx=(6, 0))
        sort_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_market_tree())

        tree = ttk.Treeview(
            frame,
            columns=("name", "type", "version", "author", "downloads", "rating"),
            show="headings",
            height=6,
        )
        tree.heading("name", text="Plugin")
        tree.heading("type", text="Type")
        tree.heading("version", text="Version")
        tree.heading("author", text="Author")
        tree.heading("downloads", text="Downloads")
        tree.heading("rating", text="Rating")
        tree.column("name", width=200, anchor="w")
        tree.column("type", width=70, anchor="center")
        tree.column("version", width=80, anchor="center")
        tree.column("author", width=120, anchor="w")
        tree.column("downloads", width=90, anchor="e")
        tree.column("rating", width=70, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=4)
        tree.bind("<Double-1>", lambda _event: self._install_market_plugin())
        self._market_tree = tree

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", padx=10, pady=(4, 8))
        ttk.Button(button_row, text="Sync Repositories", command=self._sync_repository_index).pack(side="left")
        ttk.Button(button_row, text="Install Selected", command=self._install_market_plugin).pack(
            side="left", padx=(6, 0)
        )

        repos_frame = ttk.LabelFrame(frame, text="Repositories")
        repos_frame.pack(fill="x", padx=10, pady=(0, 10))
        listbox = tk.Listbox(repos_frame, height=3)
        listbox.pack(fill="x", padx=4, pady=(4, 2))
        self._repository_listbox = listbox

        repo_controls = ttk.Frame(repos_frame)
        repo_controls.pack(fill="x", padx=4, pady=(0, 4))
        entry = ttk.Entry(repo_controls, textvariable=self._repository_entry_var)
        entry.pack(side="left", fill="x", expand=True)
        ttk.Button(repo_controls, text="Add", command=self._add_market_repository).pack(side="left", padx=(6, 0))
        ttk.Button(repo_controls, text="Remove", command=self._remove_market_repository).pack(
            side="left", padx=(6, 0)
        )

        self._refresh_repository_sources()
        self._refresh_market_tree()

    def _refresh_market_tree(self) -> None:
        tree = getattr(self, "_market_tree", None)
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)

        query = self._market_search_var.get().strip()
        filter_value = self._market_type_var.get().lower()
        sort_by = self._market_sort_var.get()
        plugin_type: PluginEntryType | None
        if filter_value in {"parser", "converter"}:
            plugin_type = cast(PluginEntryType, filter_value)
        else:
            plugin_type = None
        results = self.repository_manager.search(query=query, plugin_type=plugin_type, sort_by=sort_by)

        self._market_entries = {}
        for entry in results:
            self._market_entries[entry.id] = entry
            tree.insert(
                "",
                "end",
                iid=entry.id,
                values=(
                    entry.name,
                    entry.type,
                    entry.version,
                    entry.author,
                    entry.downloads,
                    f"{entry.rating:.1f}",
                ),
            )

    def _sync_repository_index(self) -> None:
        self._set_status("Status: 正在同步插件市场…")

        def _worker() -> None:
            success, message = self.repository_manager.sync()
            master = cast(tk.Misc, self)
            master.after(0, lambda: self._on_repository_sync_finished(success, message))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_repository_sync_finished(self, success: bool, message: str) -> None:
        self._set_status(f"Status: {message}")
        if success:
            self._refresh_market_tree()

    def _install_market_plugin(self) -> None:
        tree = getattr(self, "_market_tree", None)
        if tree is None:
            return
        selection = tree.selection()
        if not selection:
            self._set_status("Status: 请选择市场中的插件。")
            return
        entry = self._market_entries.get(selection[0])
        if entry is None:
            self._set_status("Status: 无法找到所选插件。")
            return
        success, prepared, message = self.remote_plugin_manager.prepare_install(entry.source_url)
        if message:
            self._set_status(f"Status: {message}")
        if not success or prepared is None:
            return
        if not self._show_remote_plugin_preview(prepared):
            self._set_status("Status: 安装已取消。")
            return
        success, commit_message = self.remote_plugin_manager.commit_install(prepared)
        self._set_status(f"Status: {commit_message}")
        if success:
            self.plugin_manager.load_plugins()
            self._refresh_plugin_settings_ui()
            self._refresh_remote_plugin_list()

    def _refresh_repository_sources(self) -> None:
        listbox = getattr(self, "_repository_listbox", None)
        if listbox is None:
            return
        listbox.delete(0, tk.END)
        for repo_url in self.repository_manager.list_repositories():
            listbox.insert(tk.END, repo_url)

    def _add_market_repository(self) -> None:
        url = self._repository_entry_var.get().strip()
        success, message = self.repository_manager.add_repository(url)
        self._set_status(f"Status: {message}")
        if success:
            self._repository_entry_var.set("")
            self._refresh_repository_sources()

    def _remove_market_repository(self) -> None:
        listbox = getattr(self, "_repository_listbox", None)
        if listbox is None:
            return
        selection = listbox.curselection()
        if not selection:
            self._set_status("Status: 请选择要移除的仓库。")
            return
        url = listbox.get(selection[0])
        success, message = self.repository_manager.remove_repository(url)
        self._set_status(f"Status: {message}")
        if success:
            self._refresh_repository_sources()

    def _refresh_plugin_settings_ui(self) -> None:
        parent = getattr(self, "_plugin_settings_parent", None)
        if parent is None:
            return
        self._build_plugin_settings(parent)

    def _refresh_remote_plugin_list(self) -> None:
        tree = getattr(self, "_remote_plugins_tree", None)
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)
        tree.tag_configure("update", background="#2b1a1a")
        for record in self.remote_plugin_manager.list_installed():
            tags = ("update",) if record["name"] in getattr(self, "_pending_updates", set()) else ()
            tree.insert(
                "",
                "end",
                iid=record["name"],
                values=(
                    record["display_name"],
                    record["plugin_type"],
                    record["version"],
                    record["source_url"],
                ),
                tags=tags,
            )

    def _install_remote_plugin(self) -> None:
        url = self.remote_plugin_url_var.get().strip()
        success, prepared, message = self.remote_plugin_manager.prepare_install(url)
        if message:
            self._set_status(f"Status: {message}")
        if not success or prepared is None:
            return
        if not self._show_remote_plugin_preview(prepared):
            self._set_status("Status: 安装已取消。")
            return
        success, message = self.remote_plugin_manager.commit_install(prepared)
        self._set_status(f"Status: {message}")
        if not success:
            return
        self.remote_plugin_url_var.set("")
        self.plugin_manager.load_plugins()
        self._refresh_plugin_settings_ui()
        self._refresh_remote_plugin_list()

    def _get_selected_remote_record(self) -> tuple[str, RemotePluginRecord] | None:
        tree = getattr(self, "_remote_plugins_tree", None)
        if tree is None:
            return None
        selection = tree.selection()
        if not selection:
            return None
        plugin_name = selection[0]
        record = self.remote_plugin_manager.get_record(plugin_name)
        if record is None:
            return None
        return plugin_name, record

    def _uninstall_remote_plugin(self) -> None:
        selected = self._get_selected_remote_record()
        if selected is None:
            self._set_status("Status: 请选择要卸载的插件。")
            return
        plugin_name, _ = selected
        tree = self._remote_plugins_tree
        plugin_type_value = tree.set(plugin_name, "type") if tree else "parser"
        success, message = self.remote_plugin_manager.uninstall(plugin_name)
        self._set_status(f"Status: {message}")
        if not success:
            return
        plugin_type = PluginType.PARSER if plugin_type_value == "parser" else PluginType.CONVERTER
        if self.plugin_manager.get_record(plugin_type, plugin_name):
            self.plugin_manager.set_enabled(plugin_type, plugin_name, False)
        self._refresh_plugin_settings_ui()
        self._refresh_remote_plugin_list()
        self._refresh_whitelist_ui()

    def _check_remote_updates(self) -> None:
        updates = self.remote_plugin_manager.check_updates()
        if not updates:
            self._pending_updates.clear()
            self._set_status("Status: 所有插件均为最新版本。")
            self._refresh_remote_plugin_list()
            return
        self._pending_updates = {update["name"] for update in updates}
        summary = ", ".join(f"{item['display_name']} ({item['current']}→{item['latest']})" for item in updates)
        self._set_status(f"Status: 发现更新 {summary}")
        self._refresh_remote_plugin_list()

    def _update_remote_plugin(self) -> None:
        tree = getattr(self, "_remote_plugins_tree", None)
        if tree is None:
            return
        selection = tree.selection()
        if not selection:
            self._set_status("Status: 请选择要更新的插件。")
            return
        plugin_name = selection[0]
        success, message = self.remote_plugin_manager.update_plugin(plugin_name)
        self._set_status(f"Status: {message}")
        if success:
            self.plugin_manager.load_plugins()
            self._pending_updates.discard(plugin_name)
            self._refresh_plugin_settings_ui()
            self._refresh_remote_plugin_list()

    def _show_remote_plugin_history(self) -> None:
        tree = getattr(self, "_remote_plugins_tree", None)
        if tree is None:
            return
        selection = tree.selection()
        if not selection:
            self._set_status("Status: 请选择要查看历史的插件。")
            return
        plugin_name = selection[0]
        history = self.remote_plugin_manager.list_history(plugin_name)
        if not history:
            self._set_status("Status: 当前插件没有历史版本。")
            return
        self._open_history_dialog(plugin_name, history)

    def _check_remote_dependencies(self) -> None:
        selected = self._get_selected_remote_record()
        if selected is None:
            self._set_status("Status: 请选择插件后再检查依赖。")
            return
        plugin_name, record = selected
        dependencies = record.get("dependencies", [])
        dep_list = [str(dep) for dep in dependencies] if isinstance(dependencies, list) else []
        if not dep_list:
            self._set_status("Status: 该插件未声明依赖。")
            messagebox.showinfo("依赖检查", "该插件未声明额外依赖。")
            return
        statuses = DependencyManager.check(dep_list)
        missing = [status for status in statuses if not status.satisfies]
        if not missing:
            self._set_status("Status: 所有依赖均已满足。")
            messagebox.showinfo("依赖检查", "所有依赖都已安装。")
            return
        lines = [f"{status.requirement} (当前: {status.installed_version or '未安装'})" for status in missing]
        messagebox.showwarning("依赖缺失", "\n".join(lines))
        self._set_status(f"Status: 缺失依赖 {', '.join(item.requirement for item in missing)}")

    def _install_remote_dependencies(self) -> None:
        selected = self._get_selected_remote_record()
        if selected is None:
            self._set_status("Status: 请选择插件后再安装依赖。")
            return
        plugin_name, record = selected
        dependencies = record.get("dependencies", [])
        dep_list = [str(dep) for dep in dependencies] if isinstance(dependencies, list) else []
        if not dep_list:
            self._set_status("Status: 该插件未声明依赖。")
            return
        missing = DependencyManager.missing(dep_list)
        if not missing:
            self._set_status("Status: 所有依赖已满足。")
            return

        self._set_status(f"Status: 正在安装 {plugin_name} 依赖…")

        def _worker() -> None:
            success, message = DependencyManager.install(missing)
            master = cast(tk.Misc, self)
            def _notify() -> None:
                self._set_status(f"Status: {message}")
                if success:
                    messagebox.showinfo("依赖安装", message)
                else:
                    messagebox.showerror("依赖安装", message)

            master.after(0, _notify)

        threading.Thread(target=_worker, daemon=True).start()

    def _open_history_dialog(self, plugin_name: str, history: list[RemotePluginHistoryEntry]) -> None:
        master = cast(tk.Misc, self)
        window = tk.Toplevel(master)
        window.title(f"{plugin_name} 版本历史")
        window.grab_set()

        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame, columns=("version", "saved_at", "checksum"), show="headings", height=8)
        tree.heading("version", text="Version")
        tree.heading("saved_at", text="Saved At (UTC)")
        tree.heading("checksum", text="Checksum")
        tree.column("version", width=90, anchor="center")
        tree.column("saved_at", width=180, anchor="center")
        tree.column("checksum", width=220, anchor="w")
        tree.pack(fill="both", expand=True)

        for entry in history:
            checksum = entry.get("checksum", "")
            entry_id = checksum or entry.get("saved_at", "") or f"{entry.get('version', '?')}-{id(entry)}"
            short_checksum = checksum[:12] + "…" if checksum else ""
            tree.insert(
                "",
                "end",
                iid=entry_id,
                values=(entry.get("version", "?"), entry.get("saved_at", ""), short_checksum),
            )

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", pady=(12, 0))

        def _rollback_selected() -> None:
            selected = tree.selection()
            if not selected:
                messagebox.showinfo("提示", "请选择一个历史版本。")
                return
            identifier = selected[0]
            entry = next(
                (
                    item
                    for item in history
                    if item.get("checksum") == identifier or item.get("saved_at") == identifier
                ),
                None,
            )
            if entry is None:
                messagebox.showerror("错误", "无法找到选中的历史版本。")
                return
            success, message = self.remote_plugin_manager.rollback_plugin(
                plugin_name,
                version=entry.get("version"),
                checksum=entry.get("checksum"),
            )
            self._set_status(f"Status: {message}")
            if success:
                window.destroy()
                self.plugin_manager.load_plugins()
                self._pending_updates.discard(plugin_name)
                self._refresh_plugin_settings_ui()
                self._refresh_remote_plugin_list()

        ttk.Button(button_row, text="Rollback", command=_rollback_selected).pack(side="left")
        ttk.Button(button_row, text="Close", command=window.destroy).pack(side="right")

    def _refresh_whitelist_ui(self) -> None:
        listbox = getattr(self, "_whitelist_listbox", None)
        if listbox is None:
            return
        listbox.delete(0, tk.END)
        for prefix in self.remote_plugin_manager.list_allowed_sources():
            listbox.insert(tk.END, prefix)

    def _add_allowed_source(self) -> None:
        prefix = self._whitelist_entry_var.get().strip()
        success, message = self.remote_plugin_manager.add_allowed_source(prefix)
        self._set_status(f"Status: {message}")
        if success:
            self._whitelist_entry_var.set("")
            self._refresh_whitelist_ui()

    def _remove_allowed_source(self) -> None:
        listbox = getattr(self, "_whitelist_listbox", None)
        if listbox is None:
            return
        selection = listbox.curselection()
        if not selection:
            self._set_status("Status: 请选择要移除的来源。")
            return
        prefix = listbox.get(selection[0])
        success, message = self.remote_plugin_manager.remove_allowed_source(prefix)
        self._set_status(f"Status: {message}")
        if success:
            self._refresh_whitelist_ui()

    def _show_remote_plugin_preview(self, prepared: PreparedRemotePlugin) -> bool:
        master = cast(tk.Misc, self)
        window = tk.Toplevel(master)
        window.title("插件信息预览")
        window.grab_set()

        metadata = prepared.metadata
        validation = prepared.validation
        display_name = metadata.get("name") or validation.plugin_name or "Unnamed"
        author = metadata.get("author", "Unknown")
        version = metadata.get("version", "0.0.0")
        description = metadata.get("description", "")
        dependencies = metadata.get("dependencies", [])

        body = ttk.Frame(window, padding=12)
        body.pack(fill="both", expand=True)

        rows = [
            ("Name", display_name),
            ("Class", validation.plugin_name or ""),
            ("Type", validation.plugin_type or ""),
            ("Version", version),
            ("Author", author),
            ("Source", prepared.url),
            ("Checksum", prepared.checksum[:32] + "…"),
        ]
        for label, value in rows:
            row = ttk.Frame(body)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"{label}:", width=10, anchor="w").pack(side="left")
            ttk.Label(row, text=value, wraplength=360, justify="left").pack(
                side="left", fill="x", expand=True
            )

        if description:
            ttk.Label(body, text="Description:", anchor="w").pack(fill="x", pady=(8, 0))
            desc_label = ttk.Label(body, text=description, wraplength=380, justify="left")
            desc_label.pack(fill="x")

        if dependencies:
            ttk.Label(body, text="Dependencies:").pack(anchor="w", pady=(8, 0))
            dep_text = "\n".join(f"• {dep}" for dep in dependencies)
            ttk.Label(body, text=dep_text, justify="left", wraplength=380).pack(anchor="w")
        else:
            ttk.Label(body, text="Dependencies: None").pack(anchor="w", pady=(8, 0))

        button_row = ttk.Frame(body)
        button_row.pack(fill="x", pady=(12, 0))
        confirmed = {"result": False}

        def _accept() -> None:
            confirmed["result"] = True
            window.destroy()

        def _cancel() -> None:
            window.destroy()

        ttk.Button(button_row, text="Install", command=_accept).pack(side="left")
        ttk.Button(button_row, text="Cancel", command=_cancel).pack(side="right")

        master.wait_window(window)
        return bool(confirmed["result"])

    def _on_plugin_toggle(self, plugin_type: PluginType, plugin_name: str) -> None:
        """Respond to plugin enable/disable events from the UI."""
        var = self.plugin_vars.get((plugin_type, plugin_name))
        if var is None:
            return

        enabled = bool(var.get())
        self.plugin_manager.set_enabled(plugin_type, plugin_name, enabled)
        status = "enabled" if enabled else "disabled"
        self._set_status(f"Status: Plugin {plugin_name} {status}.")
        if plugin_type is PluginType.PARSER:
            self._refresh_provider_options()

    # --- Directory Selection ---

    def _browse_download_dir(self) -> None:
        """Open a directory selection dialog."""
        initial_dir = self.download_dir_path or get_default_download_root()
        directory = filedialog.askdirectory(initialdir=initial_dir)
        if directory:
            self.download_dir_var.set(directory)

    def _on_download_dir_var_write(self, *_: object) -> None:
        """Handle changes to the download directory variable."""
        value = self.download_dir_var.get()
        self.download_dir_path = value.strip() if isinstance(value, str) else ""

    # --- Worker Count Handlers ---

    def _on_chapter_workers_change(self, event: tk.Event | None = None) -> None:
        """Handle changes to chapter worker count."""
        value = clamp_value(
            self.chapter_workers_var.get(),
            CONFIG.download.min_chapter_workers,
            CONFIG.download.max_chapter_workers,
            self._chapter_workers_value or CONFIG.download.default_chapter_workers,
        )
        if value != self.chapter_workers_var.get():
            self.chapter_workers_var.set(value)
        if value != self._chapter_workers_value or event is None:
            self._chapter_workers_value = value
            self._ensure_chapter_executor(force_reset=True)

    def _on_image_workers_change(self, event: tk.Event | None = None) -> None:
        """Handle changes to image worker count."""
        value = clamp_value(
            self.image_workers_var.get(),
            CONFIG.download.min_image_workers,
            CONFIG.download.max_image_workers,
            self._image_workers_value or CONFIG.download.default_image_workers,
        )
        if value != self.image_workers_var.get():
            self.image_workers_var.set(value)
        if value != self._image_workers_value or event is None:
            self._image_workers_value = value

    def _get_image_worker_count(self) -> int:
        """Get the current image worker count, clamped to valid range."""
        value = clamp_value(
            self._image_workers_value or CONFIG.download.default_image_workers,
            CONFIG.download.min_image_workers,
            CONFIG.download.max_image_workers,
            CONFIG.download.default_image_workers,
        )
        return min(value, CONFIG.download.max_total_image_workers)
