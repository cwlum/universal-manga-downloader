# Remote Plugin Installation Guide

Universal Manga Downloader v1.3.6 introduces the enhanced remote plugin workflow (metadata preview and whitelists). Follow these steps to safely install community plugins.

## Quick Start

1. **Find a plugin** – browse the official template under `plugin_repository/official` or the hosted GitHub repository.
2. **Copy the raw URL** – it must begin with `https://raw.githubusercontent.com/` and belong to a whitelisted source.
3. **Open the app** – Settings → Remote Plugins (Beta).
4. **Paste & install** – enter the URL, click **Install**; you will see a metadata preview dialog before the plugin is committed.

## Safety Checklist

- Only install plugins from sources you trust.
- Inspect the plugin code before installing; the preview dialog shows the declared metadata, checksum, and dependencies.
- Maintain the **Allowed Sources** list in Settings to restrict installs to trusted repositories.
- Keep a backup of `plugins/plugin_registry.json` if you plan to sync between devices.

## Registry Location

- Installed files live in the standard `plugins/` directory.
- Metadata (display name, version, author, checksum, dependencies) is recorded in `plugins/plugin_registry.json`.
- Deleting registry entries through the UI removes the corresponding file.

## Troubleshooting

| Issue | Resolution |
| --- | --- |
| "仅支持 raw.githubusercontent.com 链接" | Copy the **Raw** link from GitHub. |
| "该来源不在白名单" | Add the prefix to **Allowed Sources** in Settings, then retry. |
| Download timeout | Check proxy settings or retry with a stable network. |
| Plugin not visible after install | Click **Refresh** in Remote Plugins or restart the app. |
| Unable to uninstall | Ensure the plugin isn't selected in another task, then retry from Settings. |

## Removing Plugins

1. Open Settings → Remote Plugins.
2. Select the plugin in the list and click **Uninstall Selected**.
3. The plugin is disabled immediately and removed from disk.

## Allowed Sources

- Manage the whitelist via Settings → Remote Plugins → Allowed Sources.
- Default entry: `https://raw.githubusercontent.com/umd-plugins/official/`.
- Adding new entries requires the same host (`raw.githubusercontent.com`).

For repository maintainers, see `PLUGIN_REPOSITORY_STRUCTURE.md` for publishing workflows.
