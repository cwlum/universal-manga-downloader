## Description

Provide a clear and concise description of what this PR does.

Fixes #(issue number)

## Type of Change

Please select the relevant options:

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code refactoring
- [ ] Performance improvement
- [ ] Test coverage improvement
- [ ] Dependency update

## Changes Made

Provide a detailed list of changes:

-
-
-

## Motivation and Context

Why is this change required? What problem does it solve?

## Testing

Describe the tests you ran to verify your changes:

### Manual Testing

- [ ] Tested in GUI mode
- [ ] Tested with `--no-gui` flag
- [ ] Tested `--doctor` command
- [ ] Tested with Bato source
- [ ] Tested with MangaDex source
- [ ] Tested pause/resume functionality
- [ ] Tested cancellation

### Automated Testing

```bash
# Commands run:
ruff check .
mypy manga_downloader.py config.py umd_cli.py core/ plugins/ services/ ui/ utils/
pytest tests/ -q
```

**Test Results:**
```
Paste test results here
```

## Screenshots (if applicable)

Add screenshots to demonstrate UI changes or new features.

## Checklist

- [ ] My code follows the project's code style (ruff passes)
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published
- [ ] I have updated CHANGELOG.md with my changes
- [ ] I have checked that my changes don't introduce security vulnerabilities

## Breaking Changes

If this PR introduces breaking changes, please describe:

- What breaks
- Migration path for users
- Updated documentation

## Performance Impact

Describe any performance implications:

- [ ] No performance impact
- [ ] Performance improvement: [describe]
- [ ] Potential performance degradation: [describe and justify]

## Additional Notes

Any additional information that reviewers should know.

## Related Issues/PRs

- Related to #
- Depends on #
- Blocks #
