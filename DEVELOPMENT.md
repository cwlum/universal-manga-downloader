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
├── core/                  # Core business logic
│   ├── pdf_converter.py   # PDF generation utilities
│   └── queue_manager.py   # Thread-safe queue state management
├── services/              # External service integrations
│   └── bato_service.py    # Bato.to search and scraping
├── parsers/               # Website-specific parsers
│   ├── base_parser.py     # Parser base class
│   └── ...                # Specific parser implementations
└── tests/                 # Unit tests
    ├── test_core/         # Tests for core modules
    ├── test_parsers/      # Tests for parsers
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
pytest --cov=core --cov=parsers --cov=services
```

## Running the App

Launch the GUI from the project root:

```bash
python manga_downloader.py
```

The application will open a Tkinter window and reuse the configured download directory.

## Adding New Features

### Adding a New Parser

1. Create a new file in `parsers/` (e.g., `mysite_parser.py`)
2. Inherit from `BaseParser`
3. Implement required methods: `get_name()`, `can_parse()`, `parse()`
4. The parser will be automatically discovered

### Adding Configuration

Update `config.py` with new settings in the appropriate config class:
- `UIConfig` for UI-related settings
- `DownloadConfig` for download behavior
- `ServiceConfig` for external services
- `PDFConfig` for PDF generation

## Code Style

Review `AGENTS.md` for coding conventions before contributing changes.
