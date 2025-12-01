# Universal Manga Downloader

![Version](https://img.shields.io/badge/version-1.4.0-orange)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-yellow)
![Last Updated](https://img.shields.io/badge/last%20updated-2025--11--30-informational)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/lum-muu/universal-manga-downloader)

Universal Manga Downloader (UMD) is a Tkinter desktop app that searches Bato and MangaDex, queues chapters, downloads page images, and converts them into PDF or CBZ archives. Everything runs locally and is extensible through parser/converter plugins discovered at runtime.

## Table of Contents

- [Highlights (v1.4.0)](#highlights-v140)
- [Requirements](#requirements)
- [Install](#install)
- [Launch](#launch)
- [GUI Workflow](#gui-workflow)
- [Project Layout](#project-layout)
- [Community Plugins](#community-plugins)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Highlights (v1.4.0)

- **Remote Plugins streamlined** — the Settings tab now scrolls properly, focuses on built-in toggles plus Remote Plugins, and drops the unfinished Plugin Market panel to reduce clutter.
- **Flexible but safe installs** — power users can enable “Allow all GitHub Raw sources (use at your own risk)” after acknowledging a warning, while curated allowed sources remain default.
- **CI hardening** — GitHub Actions now runs pytest across Linux/macOS/Windows and Python 3.10–3.12, keeping coverage reporting on Ubuntu 3.11 for consistent metrics.

## Requirements

- Python **3.11+** (CI uses 3.14).
- Tkinter headers (`python3-tk` on many Linux distros; bundled on Windows/macOS).
- Git (recommended for contributing).

## Install

### Using `pipx` (recommended)
```bash
pipx install .
```
Installs the `umd` console script in an isolated environment.

### Using a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
pip install ruff mypy pytest
```
PEP 668 users should prefer `pipx` or the virtual environment above.

## Launch

```bash
umd
```

Common flags:

| Flag | Purpose |
| --- | --- |
| `-v`, `--version` | Print application and Python versions |
| `--doctor` | Run environment diagnostics (Python, Tkinter, dependencies, disk space, download path) |
| `--log-level debug` | Emit verbose logs for troubleshooting |
| `--no-gui` | Validate setup without opening Tkinter (useful for CI) |
| `--auto-update` | Reinstall the latest package before launching |
| `--config-info` | Dump current configuration values |

## GUI Workflow

1. **Browser tab** — pick Bato or MangaDex, search for a series, and open the chapter list.
2. **Queueing** — queue selected chapters, a range, everything, or paste a URL into Quick Queue.
3. **Downloads tab** — watch per-chapter progress, pause/resume/cancel, and inspect status messages.
4. **Settings tab** — pick the download directory, adjust worker counts, and enable/disable plugins.

## Project Layout

| Path | Purpose |
| --- | --- |
| `manga_downloader.py` | Thin wrapper launching the Tkinter app |
| `umd_cli.py` | Console entry point with diagnostics and headless validation |
| `ui/app.py` | Main GUI entry point orchestrating tab mixins |
| `ui/tabs/` | Browser, Downloads, Settings tab implementations |
| `core/` | Queue manager and download task orchestration |
| `services/` | Bato and MangaDex helpers |
| `plugins/` | Official built-in parser and converter plugins (bundled) |
| `community-plugins/` | Community plugin repository (for developers; users install via Remote Plugins) |
| `utils/` | File and HTTP helpers |
| `config.py` | Frozen dataclass configuration (`CONFIG`) |
| `tests/` | Pytest suites for queueing, downloads, and plugins |

**Note for users:** When you clone the repository, `plugins/` contains official built-in plugins that work out of the box. The `community-plugins/` directory is for developers who want to contribute plugins—you don't need to interact with it directly. Install community plugins via Settings → Remote Plugins instead.

## Community Plugins

UMD has a vibrant ecosystem of community-contributed parsers and converters available via the Remote Plugin system.

- **Browse**: Visit the [Plugin Wiki](https://github.com/lum-muu/universal-manga-downloader/wiki) to see all available community plugins with descriptions and installation URLs.
- **Install**: Settings → Remote Plugins lets you paste a GitHub Raw URL (from the wiki or any trusted source) to install parsers or converters immediately.
- **Safety**: Keep the curated whitelist for peace of mind, or intentionally enable “Allow all GitHub Raw sources” in Settings → Remote Plugins if you accept the additional risk.
- **CLI**: Run `umd plugins list/install/update --all/history/rollback/install-deps` for headless workflows.
- **Develop**: Want to create your own plugin? See [PLUGINS.md](PLUGINS.md) for the development guide.
- **Submit**: Follow the [Plugin Submission Guide](https://github.com/lum-muu/universal-manga-downloader/wiki/Plugin-Submission-Guide) to contribute your own plugins via PR to `community-plugins/`.
- **Architecture**: See [WIKI_BASED_PLUGIN_REPOSITORY.md](WIKI_BASED_PLUGIN_REPOSITORY.md) for how the community plugin repository works.

## Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: ui.logging_utils` | Running from a stale install | Reinstall with `pipx install . --force` or reinstall the editable package |
| GUI fails to start on Linux | Tkinter missing | Install `sudo apt install python3-tk` (or distro equivalent) |
| Downloads stay on “Paused” | Pause event still set | Click **Resume Downloads** in the Downloads tab |
| MangaDex throttles requests | Too many image workers | Lower the image worker count in Settings |

## Contributing

- New to the project? Start with [ONBOARDING.md](ONBOARDING.md).
- Day-to-day commands live in [DEVELOPMENT.md](DEVELOPMENT.md); plugin details in [PLUGINS.md](PLUGINS.md).
- Architectural decisions and threading rules are documented in [ARCHITECTURE.md](ARCHITECTURE.md).
- Please respect the non-commercial license (CC BY-NC-SA 4.0) and document behavior changes in MRs.

## License

Distributed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). See [DISCLAIMER.md](DISCLAIMER.md) for usage limits.
