# Version 1.3.2 Release Notes

## Release Date: 2025-11-24

## Summary
Version 1.3.2 focuses on code organization, maintainability, and documentation improvements. The large ui/app.py file has been refactored into modular components, making the codebase more maintainable and testable.

## What's New

### UI Component Modularization
The monolithic `ui/app.py` file (1606 lines) has been refactored into focused modules:

1. **ui/models.py** - Data Models
   - `QueueItem`: Queue widget container dataclass
   - `SearchResult`: Search result type definition
   - `SeriesChapter`: Chapter metadata type definition
   - `STATUS_COLORS`: Queue state color mapping

2. **ui/widgets.py** - Reusable UI Components
   - `MouseWheelHandler`: Cross-platform mouse wheel scroll handling
   - `clamp_value()`: Value clamping utility function
   - Extracted from ui/app.py for reusability

3. **ui/app.py** - Main Application (Refactored)
   - Now imports from ui/models and ui/widgets
   - Cleaner imports and reduced code duplication
   - Maintains all existing functionality

### Documentation Updates
- **README.md**: Updated highlights to reflect v1.3.2 features
- **CHANGELOG.md**: Comprehensive v1.3.2 changelog with all changes
- **IMPROVEMENTS.md**: Updated with v1.3.2 refactoring details
- Version badges updated to 1.3.2
- Last updated date: 2025-11-24

### Version Updates
- `pyproject.toml`: version = "1.3.2"
- `README.md`: version badge updated
- All documentation reflects v1.3.2

## Benefits

### For Developers
- **Easier to Navigate**: Related code grouped in logical modules
- **Better Testability**: Isolated components can be tested independently
- **Reduced Duplication**: Reusable utilities in dedicated modules
- **Clearer Dependencies**: Explicit imports show relationships
- **Improved Maintainability**: Smaller files are easier to understand and modify

### For Users
- **No Breaking Changes**: All existing functionality preserved
- **Same User Experience**: UI and features unchanged
- **Better Stability**: All 105 tests passing
- **Future-Proof**: Modular structure enables easier feature additions

## Technical Details

### Files Created
```
ui/models.py      - 60 lines
ui/widgets.py     - 114 lines
```

### Files Modified
```
ui/app.py         - Refactored imports, removed duplicate code
pyproject.toml    - Version updated to 1.3.2
README.md         - Highlights and version updated
CHANGELOG.md      - v1.3.2 section added
IMPROVEMENTS.md   - v1.3.2 section added
```

### Code Metrics
- **Lines Removed**: ~150 lines of duplicate code
- **Code Reusability**: +2 reusable modules
- **Maintainability**: Significantly improved with focused modules
- **Test Coverage**: 105 tests passing (no regressions)

## Installation

### New Installation
```bash
pipx install .
```

### Upgrade from 1.3.1
```bash
source .venv/bin/activate
pip install -e . --force-reinstall
```

or

```bash
pipx install . --force
```

## Verification

Run the setup script to verify installation:
```bash
./setup.sh
```

Or manually verify:
```bash
source .venv/bin/activate
umd --version  # Should show 1.3.2
pytest tests/ -q  # Should show 105 passed
```

## Migration Notes

### For Contributors
If you have existing branches based on v1.3.1:
1. The main UI application imports have changed
2. Use `from ui.models import QueueItem, SearchResult, SeriesChapter, STATUS_COLORS`
3. Use `from ui.widgets import MouseWheelHandler, clamp_value`
4. Run tests to ensure compatibility: `pytest tests/ -q`

### Backward Compatibility
- ✅ **Full backward compatibility maintained**
- ✅ All existing features work identically
- ✅ No changes to user-facing APIs
- ✅ No changes to plugin interfaces
- ✅ Configuration files unchanged

## What's Next

Future enhancements planned:
- Additional UI module extraction (search, download, settings handlers)
- Enhanced error messages with context
- Performance profiling and optimization
- Extended integration test coverage

## Testing

All tests pass successfully:
```bash
$ pytest tests/ -q
........................................................................ [ 68%]
.................................                                        [100%]
105 passed in 0.55s
```

## Acknowledgments

This release improves code organization based on best practices for maintainable Python applications, making the project more accessible to contributors.

---

**Full Changelog**: [CHANGELOG.md](CHANGELOG.md)
**Project Score**: 95/100 (maintained from v1.3.1)
