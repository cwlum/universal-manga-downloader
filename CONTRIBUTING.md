# Contributing Guide

Thank you for helping improve Universal Manga Downloader! This guide outlines the expectations for contributors and how to get changes merged smoothly.

## Core Expectations

- Work from a feature branch (for example, `feature/new-parser` or `fix/resume-race`).
- Follow the non-commercial license (CC BY-NC-SA 4.0); no telemetry, ads, or embedded secrets.
- Keep changes small and well-documented; update relevant `.md` files when behavior shifts.
- Use the shared tooling (`ruff`, `mypy`, `pytest`) and avoid `print` in production code.

## Getting Set Up

Complete the steps in [ONBOARDING.md](ONBOARDING.md) to create a virtual environment, install dependencies, and verify the GUI launches. Reactivate the venv for every session:

```bash
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

## Development Workflow

1. Sync: `git fetch --all --prune` and `git pull --ff-only` (set upstream if needed).
2. Branch: `git checkout -b feature/your-change`.
3. Code: keep commits focused with clear messages (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
4. Validate: run `ruff check .`, `mypy ...`, and `pytest tests -q`.
5. Document: update README/PLUGINS/DEVELOPMENT/ARCHITECTURE as appropriate.

## Pull Requests

Include the following in every PR:

- Summary of what changed and why.
- Tests executed (commands and manual steps).
- Screenshots/GIFs for UI updates when relevant.
- Breaking changes, if any, called out explicitly.
- Issue links (`Fixes #123`) where applicable.

## Validation Commands

| Purpose | Command |
| --- | --- |
| Lint | `ruff check .` |
| Type check | `mypy manga_downloader.py config.py umd_cli.py core/ plugins/ services/ ui/ utils/ --no-error-summary` |
| Tests | `pytest tests -q` |
| GUI smoke test | `python -m manga_downloader` (or `umd`) |

## Community Standards

- Be respectful and responsive in reviews.
- Prefer modular changes; break up large GUI work into smaller patches.
- Ask questions early—open an issue or draft PR if direction is unclear.
- Credit upstream sources and avoid copying licensed content without permission.
