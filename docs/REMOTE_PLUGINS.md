# Remote Plugin Installation Guide

Universal Manga Downloader v1.3.9 extends the remote plugin workflow with metadata previews, repository sync, CLI automation, rollback support, and dependency-aware bundles. Follow these steps to safely install community plugins.

## Quick Start

1. **Find a plugin** – either browse the official repo (`plugin_repository/official`) or open **Settings → Plugin Market (Preview)** and click **Sync Repositories** to fetch the curated index.
2. **Pick a source** – install directly from the market (search/filter/sort, then double-click) or copy any GitHub Raw URL.
3. **Open the app** – use Settings → Remote Plugins (Beta) for manual URLs/rollback/whitelists.
4. **Preview & install** – every install opens a metadata dialog (name, version, dependencies, checksum) before writing to disk.
5. **Stay updated** – click **Check Updates** (GUI) or use `umd plugins check-updates` / `umd plugins update --all` in scripts/CI.

> Prefer the terminal? Skip the GUI entirely with commands such as `umd plugins list`, `umd plugins install <URL>`, `umd plugins update MangadexEnhanced`, or `umd plugins rollback MangadexEnhanced --version 1.2.3`.

## Safety Checklist

- Only install plugins from sources you trust.
- Inspect the plugin code before installing; the preview dialog shows the declared metadata, checksum, and dependencies.
- Maintain the **Allowed Sources** list in Settings to restrict installs to trusted repositories.
- Keep a backup of `plugins/plugin_registry.json` if you plan to sync between devices.

## Registry, History & Bundles

- Installed files live in the standard `plugins/` directory. Single-file plugins end with `.py`; multi-file bundles unpack into `plugins/<PluginName>/` packages.
- Metadata (display name, version, author, checksum, dependencies, artifact type) and **history snapshots** are recorded in `plugins/plugin_registry.json`.
- Every update stores the previous version under `plugins/remote_history/<PluginName>/`; rollbacks copy back either the single file or the entire directory tree.
- Deleting registry entries through the UI removes the corresponding file/directory and its history folder.

## Plugin Market (Preview)

1. Open **Settings → Plugin Market (Preview)**.
2. Click **Sync Repositories** to fetch `index.json` from `umd-plugins/official` (or any custom repository you add).
3. Search/filter/sort the list (type, downloads, rating, updated date) to find what you need.
4. Double-click or select + **Install Selected** to run the standard validation/preview workflow—`.zip` bundles are extracted into their own package directories.
5. Maintain additional repositories via the listbox (Add/Remove) — they persist in `plugins/plugin_repositories.json`.

The market view is intentionally opt-in and non-blocking: if sync fails, the installed plugins remain untouched.

## CLI Management

The `umd` binary ships with subcommands tailored for remote plugins:

| Command | Purpose |
| --- | --- |
| `umd plugins list` | Show installed remote plugins, types, versions, and source URLs. |
| `umd plugins install <raw_url> [--force]` | Install (or replace) a plugin from a GitHub Raw URL. |
| `umd plugins uninstall <ClassName>` | Remove the plugin file and registry entry. |
| `umd plugins check-updates` | Report all available remote plugin updates. |
| `umd plugins update --all` or `umd plugins update <Name...>` | Upgrade plugins in bulk or selectively. |
| `umd plugins history <ClassName>` | Display stored snapshots (version, timestamp, checksum). |
| `umd plugins rollback <ClassName> [--version V] [--checksum HASH]` | Restore a previous version from history. |
| `umd plugins install-deps <ClassName>` | Install any missing dependencies declared by the plugin. |

All commands honor the same whitelist/registry as the GUI, making headless installations and CI automation straightforward.

## Troubleshooting

| Issue | Resolution |
| --- | --- |
| "仅支持 raw.githubusercontent.com 链接" | Copy the **Raw** link from GitHub. |
| "该来源不在白名单" | Add the prefix to **Allowed Sources** in Settings, then retry. |
| "所有插件均为最新版本" | Appears after **Check Updates** completes with no newer versions. |
| Download timeout | Check proxy settings or retry with a stable network. |
| Plugin not visible after install | Click **Refresh** in Remote Plugins or restart the app. |
| Unable to uninstall | Ensure the plugin isn't selected in another task, then retry from Settings. |
| Want to revert a bad update | Select the plugin and click **History / Rollback** (GUI) or run `umd plugins rollback <Name> --version <old>` (CLI). |

## Removing Plugins

1. Open Settings → Remote Plugins.
2. Select the plugin in the list and click **Uninstall Selected**.
3. The plugin is disabled immediately and removed from disk.

## Allowed Sources

- Manage the whitelist via Settings → Remote Plugins → Allowed Sources.
- Default entry: `https://raw.githubusercontent.com/umd-plugins/official/`.
- Adding new entries requires the same host (`raw.githubusercontent.com`).

## Updating, Dependencies & Rolling Back

- Click **Check Updates** to fetch metadata from each installed plugin; rows with updates turn shaded.
- Use **Check Dependencies** / **Install Missing Deps** (GUI) or `umd plugins install-deps <Name>` to keep requirements satisfied.
- Select a plugin and click **Update Selected** to re-download and replace it in-place, or run `umd plugins update --all` headlessly.
- Every update archives the previous version; use **History / Rollback** (GUI) or `umd plugins rollback` to recover.

For repository maintainers, see `PLUGIN_REPOSITORY_STRUCTURE.md` for publishing workflows.
