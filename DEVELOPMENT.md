# Development Guide

## Environment Setup

1. Create and activate a Python 3.11 virtual environment.
2. Install runtime dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install tooling dependencies:
   ```bash
   pip install ruff mypy
   ```

## Quality Gates

- **Linting**: `ruff check .`
- **Type checking**: `mypy .`

Both commands run in CI. Ensure they pass locally before opening a pull request.

## Running the App

Launch the GUI from the project root:

```bash
python manga_downloader.py
```

The application will open a Tkinter window and reuse the configured download directory. Review `AGENTS.md` for coding conventions before contributing changes.
