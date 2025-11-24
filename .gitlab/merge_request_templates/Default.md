## Description

Provide a clear and concise description of what this MR does.

Closes #(issue number)

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Code refactoring
- [ ] Performance improvement
- [ ] Test coverage improvement

## Changes Made

-
-
-

## Testing

### Manual Testing

- [ ] Tested in GUI mode
- [ ] Tested with `--no-gui` flag
- [ ] Tested with Bato source
- [ ] Tested with MangaDex source

### Automated Testing

```bash
ruff check .
mypy manga_downloader.py config.py umd_cli.py core/ plugins/ services/ ui/ utils/
pytest tests/ -q
```

**Results:**
```
Paste test results here
```

## Checklist

- [ ] My code follows the project's code style (ruff passes)
- [ ] I have performed a self-review
- [ ] I have commented my code where needed
- [ ] I have updated documentation
- [ ] I have added/updated tests
- [ ] All tests pass locally
- [ ] I have updated CHANGELOG.md

## Additional Notes

Any additional information for reviewers.
