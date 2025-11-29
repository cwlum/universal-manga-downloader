# Remote Plugin Installation Guide

Universal Manga Downloader v1.3.5 introduces remote plugin support. Follow these steps to safely install community plugins.

## Quick Start

1. **Find a plugin** – browse the official template under `plugin_repository/official` or the hosted GitHub repository.
2. **Copy the raw URL** – it must begin with `https://raw.githubusercontent.com/`.
3. **Open the app** – Settings → Remote Plugins (Beta).
4. **Paste & install** – enter the URL, click **Install**, and the plugin loads immediately.

## Safety Checklist

- Only install plugins from sources you trust.
- Inspect the plugin code before installing; remote manager only performs lightweight validation.
- Keep a backup of `plugins/plugin_registry.json` if you plan to sync between devices.

## Registry Location

- Installed files live in the standard `plugins/` directory.
- Metadata is recorded in `plugins/plugin_registry.json` (name, type, source URL, install date).
- Deleting registry entries through the UI removes the corresponding file.

## Troubleshooting

| Issue | Resolution |
| --- | --- |
| "仅支持 raw.githubusercontent.com 链接" | Copy the **Raw** link from GitHub. |
| Download timeout | Check proxy settings or retry with a stable network. |
| Plugin not visible after install | Click **Refresh** in Remote Plugins or restart the app. |
| Unable to uninstall | Ensure the plugin isn't selected in another task, then retry from Settings. |

## Removing Plugins

1. Open Settings → Remote Plugins.
2. Select the plugin in the list and click **Uninstall Selected**.
3. The plugin is disabled immediately and removed from disk.

For repository maintainers, see `PLUGIN_REPOSITORY_STRUCTURE.md` for publishing workflows.
