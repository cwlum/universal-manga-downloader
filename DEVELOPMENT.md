# Development Guide

## Environment Setup

1. Create and activate a Python 3.11 virtual environment.
2. Install runtime dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install tooling dependencies:
   ```bash
   pip install ruff mypy pytest
   ```

## Project Structure

```
bato-downloader/
├── config.py              # Application configuration and constants
├── manga_downloader.py    # Main GUI application
├── plugins/               # Parser and converter plugins
│   ├── base.py            # Base classes + plugin manager
│   ├── bato_parser.py     # Example parser plugin
│   ├── pdf_converter.py   # Example converter plugin
│   └── cbz_converter.py   # Example converter plugin
├── core/                  # Core business logic
│   └── queue_manager.py   # Thread-safe queue state management
├── services/              # External service integrations
│   └── bato_service.py    # Bato.to search and scraping
└── tests/                 # Unit tests
    ├── test_core/         # Tests for core modules
    ├── test_plugins/      # Tests for plugin infrastructure
    └── test_services/     # Tests for services
```

## Quality Gates

- **Linting**: `ruff check .` (auto-fix with `ruff check --fix .`)
- **Type checking**: `mypy .`
- **Testing**: `pytest -v`

All commands run in CI. Ensure they pass locally before opening a pull request.

## Running Tests

Run all tests:
```bash
pytest
```

Run specific test file:
```bash
pytest tests/test_core/test_queue_manager.py
```

Run with coverage:
```bash
pytest --cov=core --cov=plugins --cov=services
```

## Running the App

Launch the GUI from the project root:

```bash
python manga_downloader.py
```

The application will open a Tkinter window and reuse the configured download directory.

## Adding New Features

### Adding a Parser Plugin

1. Create a new file in `plugins/` (e.g., `mysite.py`)
2. Subclass `BasePlugin` from `plugins.base`
3. Implement `get_name()`, `can_handle(url)`, and `parse(soup, url)`
4. Optional: override `on_load()` / `on_unload()` for setup or cleanup
5. The plugin loader will automatically discover and register it at startup

### Adding a Converter Plugin

1. Create a file in `plugins/` (e.g., `epub_converter.py`)
2. Subclass `BaseConverter`
3. Implement `get_name()`, `get_output_extension()`, and `convert(image_files, output_dir, metadata)`
4. Use `ChapterMetadata` from `plugins.base` for consistent naming
5. Make sure the plugin complies with the non-commercial license requirements

### Adding Configuration

Update `config.py` with new settings in the appropriate config class:
- `UIConfig` for UI-related settings
- `DownloadConfig` for download behavior
- `ServiceConfig` for external services
- `PDFConfig` for PDF generation

## Code Style

Review **[AGENTS.md](AGENTS.md)** for AI-specific coding conventions and **[ONBOARDING.md](ONBOARDING.md)** for general coding standards before contributing changes.

### Key Principles

1. **Type Safety**: Use comprehensive type hints (Python 3.10+ syntax)
2. **Logging**: Use `logging` module instead of `print()` statements
3. **Error Handling**: Catch specific exceptions and log with context
4. **Docstrings**: Document public functions and classes
5. **Testing**: Write tests for new features and bug fixes

## Git Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `refactor/description` - Code improvements
- `docs/description` - Documentation updates

### Commit Messages

Follow conventional commits format:

```
feat: Add EPUB converter plugin
fix: Resolve race condition in queue manager
docs: Update ARCHITECTURE.md with threading model
refactor: Extract UI helpers into utils module
```

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear, atomic commits
3. Run quality checks (ruff, mypy, pytest)
4. Push to your fork
5. Open a pull request with a clear description
6. Address review feedback
7. Maintainer will merge when approved

## Troubleshooting

### Import Errors

If you see import errors, ensure:
- Virtual environment is activated
- All dependencies are installed: `pip install -r requirements.txt`
- You're running from the project root directory

### Type Checking Errors

If mypy reports errors:
- Add type hints to function signatures
- Use `# type: ignore[error-code]` sparingly with comments
- Update `pyproject.toml` if needed for project-wide settings

### Test Failures

If tests fail:
- Run tests individually: `pytest tests/test_core/test_queue_manager.py -v`
- Check for missing mocks or fixtures
- Ensure test data files exist if needed

## Getting Help

- Open an issue on GitHub for bugs or feature requests
- Tag issues with `question` for help
- Check existing issues before creating new ones
- See **[ONBOARDING.md](ONBOARDING.md)** for common developer tasks
