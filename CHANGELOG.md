# Changelog

All notable changes to Universal Manga Downloader will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.9] - 2025-11-29

### Added
- `plugins/dependency_manager.py` plus GUI + CLI flows for checking/installing missing plugin requirements (`umd plugins install-deps`).
- ZIP/multi-file plugin installation with package-aware history/rollback and PluginLoader support for directory modules.
- Remote Plugins UI buttons for dependency inspection/installation and market installs for `.zip` bundles.

### Changed
- Remote plugin registry schema now records `artifact_type` so packages and single files share the same update/rollback path.
- Plugin repository index includes `artifact_type` metadata; docs highlight the v0.5 roadmap progress.
- CLI `plugins install/update` commands emit dependency prompts instead of silently failing at runtime.

## [1.3.8] - 2025-11-29

### Added
- Remote plugin history snapshots and rollback controls (GUI + `umd plugins history/rollback`).
- Plugin Market (Preview) with RepositoryManager sync, search/filter/sort UI, and multi-repository persistence.
- CLI subcommands (`umd plugins list/install/uninstall/check-updates/update/history/rollback`) plus pytest coverage for remote manager, repository manager, and CLI flows.

### Changed
- Settings tab reorganized: Remote Plugins gains History dialog, and the new Plugin Market panel wires into the whitelist + installer preview pipeline.
- Documentation and roadmaps updated for v0.3 completion (rollback/CLI) and v0.4 groundwork (market + repository sync); plugin repository structure now tracks Phase 3 as delivered.

### Fixed
- Regression coverage prevents remote plugin updates from losing previous versions and validates repository index parsing for malformed entries.

## [1.3.7] - 2025-11-29

### Added
- Version comparison and remote update pipeline (`plugins/version_manager.py` + `RemotePluginManager.check_updates/update_plugin`).
- Settings → Remote Plugins now exposes “Allowed Sources”, “Check Updates”, “Update Selected”, and row highlighting for outdated plugins.

### Changed
- Registry schema v2 entries persist display name/version/checksum/dependencies used for update decisions.
- Documentation (README, Remote Plugin Guide, roadmap) updated for the v0.3 workflow.

### Fixed
- Additional tests (`tests/test_plugins/test_remote_manager.py`) cover whitelist management and update flows to prevent regressions.

## [1.3.6] - 2025-11-29

### Added
- Registry schema v2 with metadata (display name, version, checksum, dependencies) and source whitelist tracking.
- Tkinter Remote Plugins UI now shows an install preview dialog and "Allowed Sources" list with add/remove controls.
- `plugins/metadata_parser.py` shared helper extracts metadata fields for the installer and plugin repository tooling.

### Changed
- README / documentation updated to describe the new whitelist workflow and preview dialog.
- Roadmap/structure docs mark v0.2 completed and baseline bumped to v1.3.6.

### Fixed
- Additional pytest coverage for the remote manager covering metadata, whitelist, and upgrade paths.

## [1.3.5] - 2025-11-29

### Added
- Remote plugin manager (`plugins/remote_manager.py`) with registry tracking, URL validation, and Tkinter management UI.
- Settings → Remote Plugins section enabling install/refresh/uninstall workflows without restarting.
- `plugin_repository/official` scaffold (README, sample plugins, scripts, GitHub Actions, website assets) to serve as the community wiki/repo.
- Documentation updates covering remote plugin installation (`docs/REMOTE_PLUGINS.md`) and sharing guidance in `PLUGINS.md`.

### Changed
- README highlights bumped to v1.3.5 and include a Remote Plugins (Beta) section.
- Roadmap/structure documents now include strike-through tracking for completed phases.

### Fixed
- Added pytest coverage for the remote manager install/uninstall flows to guard against registry regressions.

## [1.3.4] - 2025-11-29

### Added
- Regression tests for HTTP helper proxy sanitization, MangaDex service wiring, and CLI auto-update env handling.

### Changed
- Unified HTTP stack so CloudScraper, MangaDex `requests.Session`, and CLI upgrade routines all disable `trust_env` and inject sanitized IPv6-aware proxies.
- Release documentation (README badges/highlights) refreshed for v1.3.4.

### Fixed
- `Bato`/`MangaDex` searches failing with `Failed to parse: http://::1:6152` whenever macOS reports loopback proxies.
- `umd --auto-update` pip reinstalls aborting with proxy parse errors.

## [1.3.3] - 2025-11-26

### Added
- Download failure cleanup functionality with safety checks (utils/file_utils.py)
- Search debounce mechanism to prevent concurrent search requests
- Enhanced error message formatting with HTTP status codes and connection types
- 15+ new UI component unit tests covering business logic
- Type annotations for mixin classes

### Changed
- **Major refactor**: Split monolithic `ui/app.py` (1544 lines) into modular mixins:
  - `ui/tabs/browser_tab.py` (741 lines) - Search, series, chapter selection
  - `ui/tabs/downloads_tab.py` (539 lines) - Queue management, progress display
  - `ui/tabs/settings_tab.py` (196 lines) - Settings, plugin management
  - `ui/app.py` reduced to 454 lines - Main entry point
- Renamed `_pause_event` to `_can_proceed_event` for clearer semantics
- Improved test coverage to 116 passing tests

### Fixed
- MyPy type checking compatibility for mixin pattern
- Unused imports in test files and browser_tab.py

## [1.3.2] - 2025-11-24

### Added
- Pre-commit hooks configuration for automated code quality checks
- Comprehensive CHANGELOG.md for version tracking
- Rate limiting implementation with token bucket algorithm
- Circuit breaker pattern for fault tolerance
- Enhanced URL validation and input sanitization (utils/validation.py)
- Integration tests for download workflow
- UI component tests for better coverage
- Edge case tests for error handling scenarios
- CODE_OF_CONDUCT.md for community guidelines
- SECURITY.md policy document with vulnerability reporting process
- Issue and PR templates for GitHub and GitLab
- Dependabot configuration for automated dependency updates
- MouseWheelHandler utility class (ui/widgets.py)
- UI data models module (ui/models.py)
- Setup script (setup.sh) for easier onboarding

### Changed
- Pinned all dependency versions for reproducible builds
- Refactored UI components into modular structure
- Enhanced error handling with more specific exceptions
- Improved test coverage to 105+ passing tests
- Updated documentation to reflect current codebase
- Enhanced README with current feature highlights

### Fixed
- Race condition in ScraperPool thread safety
- Resource leak in PDF converter image handling
- Path traversal vulnerability in download directory preparation
- Thread safety issues in HTTP client pooling

### Security
- Added comprehensive input validation for URLs and file paths
- Implemented circuit breaker to prevent cascading failures
- Fixed path traversal vulnerabilities
- Added security scanning with pip-audit in CI/CD

## [1.3.1] - 2025-11-17

### Fixed
- Updated coverage report configuration to use Cobertura format
- Improved CI/CD workflows with security scans and performance tests

### Changed
- Enhanced caching in MangaDexService for better performance
- Streamlined AGENTS.md documentation
- Updated mypy paths for UI reorganization
- Updated version badge date

## [1.3.0] - 2025-11-10

### Added
- Stable pause/resume functionality that halts in-flight workers via shared event
- MangaDex browser support with parser plugin
- Plugin system with automatic discovery
- `--doctor` CLI flag for environment diagnostics
- `--config-info` CLI flag to dump current configuration
- Performance test suite separated from main tests

### Changed
- `manga_downloader.py` now serves as compatibility shim while `ui/app.py` hosts the UI
- Cleaner plugin surface with parsers/converters under `plugins/` directory
- Extracted download logic into DownloadTask class for better separation of concerns
- Improved chapter naming conventions

### Fixed
- Repository URLs migrated from cwlum to lummuu
- GitLab CI YAML syntax corrections
- Test expectations to match sanitize_filename implementation
- Ruff and code quality issues

## [1.2.1] - 2025-11-01

### Added
- GitLab CI/CD pipeline configuration
- Dual repository support (GitLab primary, GitHub mirror)

### Changed
- Migrated documentation from GitHub-centric to GitLab
- Updated onboarding documentation for new contributors
- Improved CLI workflow and documentation

### Fixed
- Various stability and UX improvements
- Code quality issues identified by Ruff

## [1.2.0] - 2025-10-20

### Added
- Bato and MangaDex service integration
- PDF and CBZ converter plugins
- Thread-safe queue manager with proper locking
- Configuration via frozen dataclasses
- Comprehensive documentation suite (ARCHITECTURE, DEVELOPMENT, PLUGINS, ONBOARDING)

### Changed
- Refactored threading model with clear boundaries
- Improved error handling and logging throughout
- Enhanced UI with dark theme support (sv-ttk)

## [1.0.0] - 2025-09-15

### Added
- Initial release of Universal Manga Downloader
- Tkinter-based desktop GUI
- Basic search functionality for manga sources
- Chapter queueing and download management
- PDF export functionality
- Basic plugin system

[Unreleased]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.3.9...HEAD
[1.3.9]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.3.8...v1.3.9
[1.3.8]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.3.7...v1.3.8
[1.3.7]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.3.6...v1.3.7
[1.3.6]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.3.5...v1.3.6
[1.3.5]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.3.4...v1.3.5
[1.3.4]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.3.3...v1.3.4
[1.3.3]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.3.2...v1.3.3
[1.3.2]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.3.1...v1.3.2
[1.3.1]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.3.0...v1.3.1
[1.3.0]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.2.1...v1.3.0
[1.2.1]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.2.0...v1.2.1
[1.2.0]: https://gitlab.com/lummuu/universal-manga-downloader/compare/v1.0.0...v1.2.0
[1.0.0]: https://gitlab.com/lummuu/universal-manga-downloader/releases/tag/v1.0.0
