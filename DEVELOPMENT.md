# Development Guide

This guide covers the day-to-day workflow for contributing to Universal Manga Downloader (UMD) 1.3.0.

## Workflow Overview

- Use a dedicated branch per change (for example, `feature/pause-status` or `fix/mangadex-timeout`).
- Sync before starting work: `git fetch --all --prune` then `git pull --ff-only` (set an upstream if needed).
- Keep commits focused and descriptive (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- Update documentation alongside behavior changes and keep logging consistent (`logging` module only).

## Environment

Activate the `.venv` created during onboarding and ensure the editable install is present:

```bash
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
pip install -r requirements.txt
pip install ruff mypy pytest
```

Re-run the installs after pulling dependency changes.

## Core Commands

| Purpose | Command |
| --- | --- |
| Lint | `ruff check .` |
| Type check | `mypy manga_downloader.py config.py umd_cli.py core/ plugins/ services/ ui/ utils/ --no-error-summary` |
| Tests | `pytest tests -q` |
| GUI | `python -m manga_downloader` (or `umd`) |
| Diagnostics | `umd --doctor` |

Run lint, type, and test checks before pushing. CI runs the same suite.

## Coding Notes

- Type hints use Python 3.11+ syntax (`list[str]`, `| None`).
- Guard Tkinter updates from worker threads via `after(...)`.
- When touching download logic, verify pause/resume and cancellation on a long-running chapter.
- Keep plugin behavior defensive—return `None` on parse/convert failures and rely on shared services for network access.

## Pull Request Checklist

- Branch is rebased on the target base (usually `main`).
- `ruff`, `mypy`, and `pytest` all pass locally.
- Docs updated where behavior or workflows changed.
- PR description includes summary, motivation, tests executed, and any screenshots for UI tweaks.
- Reference related issues (for example, `Fixes #123`).

## Troubleshooting

| Issue | Diagnosis | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: ui.logging_utils` | Editable install missing | Re-run `pip install -e .` inside the venv |
| Tkinter window will not open | Tk not installed or display blocked | Install `python3-tk` (Linux) or ensure a display is available |
| Ruff/Mypy fail in CI but not locally | Not using the project venv | Reactivate `.venv` and reinstall dependencies |
| Downloads never resume | Pause event unset | Confirm resume logic calls `_pause_event.set()` |

Need more context? See [ARCHITECTURE.md](ARCHITECTURE.md) for design details and [PLUGINS.md](PLUGINS.md) when extending parsers/converters.
