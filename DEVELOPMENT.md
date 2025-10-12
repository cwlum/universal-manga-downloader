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

Review `AGENTS.md` for coding conventions before contributing changes.
