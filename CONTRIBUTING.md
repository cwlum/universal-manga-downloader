# Contributing Guide

Thank you for your interest in improving Universal Manga Downloader! This project thrives on community-driven plugins and quality contributions. The guidelines below help us keep the codebase maintainable, type-safe, and respectful of the non-commercial spirit of the project.

## 🧭 Getting Started

1. Fork the repository and clone your fork.
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-change
   ```
3. Install dependencies into a Python 3.11 virtual environment:
   ```bash
   pip install -r requirements.txt
   pip install ruff mypy pytest black
   ```
4. Configure the repo for pre-commit hooks or formatting tools you rely on (optional but encouraged).

## 🔌 Plugin Development

Plugins live in the `plugins/` directory and are auto-discovered at runtime. The application ships with a loader that scans for `.py` files (excluding `__init__.py` and hidden files) and registers each plugin safely using `importlib`.

### Parser Plugins

- Subclass `BasePlugin` from `plugins.base`.
- Implement the required methods:
  - `get_name(self) -> str`
  - `can_handle(self, url: str) -> bool`
  - `parse(self, soup: BeautifulSoup, url: str) -> ParsedChapter | None`
- Optional lifecycle hooks:
  - `on_load(self) -> None`
  - `on_unload(self) -> None`
- Return sanitized titles/chapters using `BasePlugin.sanitize_filename` to avoid filesystem issues.

### Converter Plugins

- Subclass `BaseConverter` from `plugins.base`.
- Implement:
  - `get_name(self) -> str`
  - `get_output_extension(self) -> str`
  - `convert(self, image_files: Sequence[Path], output_dir: Path, metadata: ChapterMetadata) -> Path | None`
- Use the `ChapterMetadata` TypedDict to name files consistently.
- Report failures via exceptions or `None`; the GUI surfaces log messages for users.

### Non-Commercial Requirement

All plugins **must** comply with the repository’s CC BY-NC-SA 4.0 license:
- No telemetry, tracking pixels, advertising SDKs, or monetization logic.
- Do not embed API keys or secrets—use environment variables or documentation instead.
- Cite any third-party datasets or code you adapt.

## 🧪 Testing & Quality Gates

Before opening a pull request, run the full suite of checks from the project root:

```bash
ruff check .
mypy .
pytest -v
```

- Keep code type-hinted (PEP 484) and follow PEP 8 formatting. We recommend `black` for consistent formatting.
- Fix or locally suppress lint findings; avoid disabling lints globally.
- Add or update tests when you introduce new behavior (e.g., new plugin types or GUI features).

## 📮 Pull Request Process

1. Ensure your branch is rebased on the latest `main`.
2. Update documentation when behavior changes (README, DEVELOPMENT.md, docs/).
3. Describe your change clearly in the PR template:
   - Summary of the feature or fix.
   - Testing steps and commands executed.
   - Any follow-up work or limitations.
4. Link to related issues or discussions.
5. Submit the PR; reviewers may request adjustments or additional tests.

## 🤝 Community Expectations

- Be respectful in issues and PR discussions.
- Prefer modular, testable designs; large GUI changes should be broken into focused commits.
- When in doubt, open an issue to discuss ideas before investing significant effort.

We appreciate every contribution—thank you for helping us build a universal, community-first manga downloader!
