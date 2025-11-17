# AI Agent Guidelines for Universal Manga Downloader

These instructions are the source of truth for AI agents working on this repository. Follow them to keep contributions consistent, type-safe, and easy for maintainers to review.

## Quick Start Checklist

- Read `ARCHITECTURE.md`, `ONBOARDING.md`, and `DEVELOPMENT.md`.
- Understand the plugin architecture (`plugins/base.py`) before altering parser/converter behavior.
- Locate relevant files before proposing changes.
- Verify you are on a feature branch (not `main`).

## Mandatory Workflow

### Environment Setup (blocking)

Run the following before making code changes:

```bash
git fetch --all --prune
git pull --ff-only          # if tracking is configured
python3 -m pip install -r requirements.txt
python --version            # ensure 3.11+
pip list | grep -E "(requests|beautifulsoup4|Pillow|cloudscraper|sv-ttk)"
```

If any step fails, stop and report the issue.

### Implementation Cycle

1. Understand the request fully before coding.
2. Create a feature branch.
3. Make focused changes with clear intent.
4. Run quality checks: `ruff check .` and `mypy .`
5. Commit with descriptive messages.
6. Push and prepare a PR that documents changes, tests, and any breaking notes.

## Code Standards

- Always use `from __future__ import annotations` and Python 3.11+ typing (`list[str]`, `| None`).
- Prefer concrete types (for example, `TypedDict`, `dataclass`) and use `TYPE_CHECKING` to break cycles.
- Logging: `logger.debug/info/warning/error/exception` with `%s` formatting. Never use `print` or f-strings inside log calls.
- Error handling: catch specific exceptions; avoid bare `except`. Return `None` from plugins on recoverable failures.
- Docstrings: include arguments, return values, and raised exceptions for public functions.

## Architecture Guardrails

- **Plugin system**: add new functionality by creating parsers/converters in `plugins/`. Avoid modifying `plugins/base.py` unless absolutely required.
- **Thread safety**: use `QueueManager` for queue mutations. Schedule UI updates via `after(...)`; never touch Tk widgets from worker threads.
- **Configuration**: add or change settings in `config.py` and use `CONFIG.section.field` instead of hardcoded values.
- **File operations**: rely on helpers in `utils/file_utils.py` for directories, filenames, and disk checks.

## Quality Gates

Before committing, run:

```bash
ruff check .
mypy manga_downloader.py config.py umd_cli.py core/ plugins/ services/ ui/ utils/ --no-error-summary
python manga_downloader.py  # manual GUI sanity check
```

Testing guidelines:
- Manual UI checks for pause/resume, cancellation, and plugin toggling.
- Pytest for plugins and queue/download logic when adding or changing behavior.

## Common Tasks

### Add a Parser Plugin
1. Create `plugins/<site>_parser.py` inheriting `BasePlugin`.
2. Implement `get_name`, `can_handle`, and `parse` returning `ParsedChapter | None`.
3. Avoid network calls inside the plugin; use or extend `services/`.
4. Test with `pytest tests/test_plugins -q` and a manual GUI run.

### Add a Converter Plugin
1. Create `plugins/<format>_converter.py` inheriting `BaseConverter`.
2. Implement `get_name`, `get_output_extension`, and `convert`.
3. Write into the provided `output_dir` only; return `None` on failure.

### Update Documentation
- User-facing changes → `README.md`
- Developer workflow → `DEVELOPMENT.md`, `ONBOARDING.md`
- Architecture/threading → `ARCHITECTURE.md`
- Plugin APIs → `PLUGINS.md`
- Agent rules → `AGENTS.md`

### Fix a Bug or Refactor
- Reproduce the issue, add targeted fixes, and keep commits small.
- Validate pause/resume and queue state when altering download logic.
- Run lint, type checks, and relevant tests.

## Pitfalls to Avoid

- Skipping environment setup or editable installs.
- Modifying `manga_downloader.py`, `plugins/base.py`, or `config.py` without understanding ripple effects.
- Ignoring type errors or silencing lint without justification.
- Accessing Tk widgets from worker threads.
- Hardcoding configuration values instead of using `CONFIG`.
- Poor logging (missing context) or bare `except` blocks.
- Forgetting documentation or edge case tests (missing elements, malformed input, network failures).

## Decision Framework

1. Is this a parser/converter addition? → Put it in `plugins/`.
2. Is it a bug fix? → Locate the module, add a focused fix, and test.
3. Is it a refactor? → Run tests first, refactor incrementally.
4. Is it a new feature touching architecture? → Ask for confirmation before large changes.
5. Unsure about thread safety, plugin base changes, or breaking behavior? → Stop and ask.

## Commit Message Conventions

```
feat: Add EPUB converter plugin
fix: Resolve race condition in queue manager
docs: Update architecture documentation
refactor: Extract UI helpers into utils module
test: Add tests for queue state transitions
chore: Update dependencies
style: Fix linting issues
```

## Reference Commands

| Task | Command |
| --- | --- |
| Setup venv | `python3 -m venv .venv && source .venv/bin/activate` |
| Install runtime deps | `pip install -r requirements.txt` |
| Editable install | `pip install -e .` |
| Lint | `ruff check .` |
| Type check | `mypy manga_downloader.py config.py umd_cli.py core/ plugins/ services/ ui/ utils/ --no-error-summary` |
| Run app | `python -m manga_downloader` (or `umd`) |
| Tests | `pytest tests -q` |
| Git status | `git status` |

The goal: maintainable, type-safe, well-documented code that new contributors can run immediately. When in doubt, prefer clarity over cleverness and ask before making breaking changes.
