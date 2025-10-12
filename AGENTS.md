# Agent Guidelines

- Target Python 3.11 and keep the codebase type-hinted. Prefer concrete types (`TypedDict`, `dataclass`) over raw dictionaries when storing structured data.
- Use `logging` instead of `print` for all runtime diagnostics. Configure loggers at module scope.
- Run `ruff check .` and `mypy .` before completing work. Fix or suppress violations locally rather than disabling global rules.
- GUI code should separate UI construction from business logic where practical. When manipulating Tk widgets, prefer helper functions or small dedicated classes instead of monolithic methods.
- Keep dependencies in `requirements.txt` for runtime needs only. Tooling dependencies belong in the GitHub Actions workflow or project configuration.
- Update relevant documentation (e.g., `README.md`, `DEVELOPMENT.md`) when behaviour changes or new workflows are introduced.
- Avoid introducing runtime package installation logic in new modules—surface missing dependencies via documentation or installation instructions instead.
