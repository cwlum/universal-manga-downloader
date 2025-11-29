# Universal Manga Downloader

![Version](https://img.shields.io/badge/version-1.3.7-orange)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-yellow)
![Last Updated](https://img.shields.io/badge/last%20updated-2025--11--29-informational)
[![GitLab](https://img.shields.io/badge/GitLab-Repository-orange?logo=gitlab)](https://gitlab.com/lummuu/universal-manga-downloader)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/cwlum/universal-manga-downloader)

Universal Manga Downloader (UMD) is a Tkinter desktop app that searches Bato and MangaDex, queues chapters, downloads page images, and converts them into PDF or CBZ archives. Everything runs locally and is extensible through parser/converter plugins discovered at runtime.

## Highlights (v1.3.7)

- **Remote plugin manager v0.3** — adds semantic version comparisons, remote update checks, and in-place updates with checksum validation.
- **Settings → Remote Plugins** now features “Check Updates” / “Update Selected”, row highlighting for pending updates, and expanded whitelist controls.
- Registry schema v2 captures version metadata per entry; tests now cover upgrade workflows and whitelist operations.

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
| `plugins/` | Parser and converter plugins (auto-discovered) |
| `utils/` | File and HTTP helpers |
| `config.py` | Frozen dataclass configuration (`CONFIG`) |
| `tests/` | Pytest suites for queueing, downloads, and plugins |

## Remote Plugins (Beta)

- Browse the staging repository under `plugin_repository/official` (or host it on GitHub as-is).
- Use Settings → Remote Plugins to manage the whitelist, preview metadata (name, version, dependencies), and install/uninstall community plugins.
- Registry lives in `plugins/plugin_registry.json`; refer to [`docs/REMOTE_PLUGINS.md`](docs/REMOTE_PLUGINS.md) for safety tips and troubleshooting.

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
