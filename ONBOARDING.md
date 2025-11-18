# Developer Onboarding

Welcome! This guide gets you from clone to a working Universal Manga Downloader (UMD) environment with the quality gates ready to run.

## Prerequisites

- Python **3.11+** (CI runs 3.14)
- Git
- Tkinter headers (`python3-tk` on most Linux distros; bundled on Windows/macOS)
- `pipx` (optional, recommended for global installs)

## Setup (5 Steps)

1. Clone the repository
   ```bash
   git clone https://gitlab.com/lummuu/universal-manga-downloader.git
   cd universal-manga-downloader
   ```
2. Create a virtual environment (recommended for PEP 668 systems)
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. Install runtime and editable package
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```
4. Install development tooling
   ```bash
   pip install ruff mypy pytest
   ```
5. Confirm the interpreter and key packages
   ```bash
   python --version
   pip list | grep -E "(requests|beautifulsoup4|Pillow|cloudscraper|sv-ttk)"
   ```

> If `pip` is blocked by system package management, stay inside the `.venv` above or use `pipx install .` to isolate the install.

## Verify the Application

- Run diagnostics: `umd --doctor`
- Launch the GUI: `umd` (or `python -m manga_downloader`)
- Inspect configuration: `umd --config-info`

Confirm you can search Bato/MangaDex, view chapters, and queue a download; this exercises plugin discovery, HTTP clients, and converters.

## Quality Gates

Execute from the repository root with the virtual environment activated:

```bash
ruff check .
mypy manga_downloader.py config.py umd_cli.py core/ plugins/ services/ ui/ utils/ --no-error-summary
pytest tests -q
```

## Where to Go Next

- [DEVELOPMENT.md](DEVELOPMENT.md) — day-to-day workflow, branch/commit guidance, and commands.
- [ARCHITECTURE.md](ARCHITECTURE.md) — threading boundaries, plugin discovery, and data flow.
- [PLUGINS.md](PLUGINS.md) — how to extend UMD with new parsers or converters.
