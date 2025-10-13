# Release Process Guide

## 📦 Overview

This project uses [Release Please](https://github.com/googleapis/release-please) for automated versioning and changelog generation based on [Conventional Commits](https://www.conventionalcommits.org/).

## 🚀 How It Works

### Automatic Process

1. **Developer creates PR with conventional commits**
   - `feat:` → Minor version bump (current release is 1.1.0)
   - `fix:` → Patch version bump (current release is 1.1.0)
   - `BREAKING CHANGE:` → Major version bump (current release is 1.1.0)

2. **PR is merged to main**
   - GitHub Action triggers Release Please workflow

3. **Release Please creates a release PR**
   - Updates `CHANGELOG.md`
   - Updates `.release-please-manifest.json`
   - Title: `chore(main): release X.Y.Z`
   - Label: `autorelease: pending`

4. **Maintainer merges release PR**
   - Release Please automatically:
     - Creates GitHub Release
     - Generates release notes
     - Tags the commit with `vX.Y.Z`

### Commit Types

| Type | Release? | Version Change | Example |
|------|----------|----------------|---------|
| `feat:` | ✅ Yes | Minor | `feat: add user authentication` |
| `fix:` | ✅ Yes | Patch | `fix: resolve memory leak` |
| `perf:` | ✅ Yes | Patch | `perf: optimize image loading` |
| `refactor:` | ❌ No | - | `refactor: extract PDF logic` |
| `docs:` | ❌ No | - | `docs: update README` |
| `test:` | ❌ No | - | `test: add unit tests` |
| `chore:` | ❌ No | - | `chore: update dependencies` |
| `style:` | ❌ No | - | `style: format code` |
| `ci:` | ❌ No | - | `ci: update workflow` |

## 📝 Manual Version Updates

### README.md Version Badge

**Current Limitation**: Release Please's `extra-files` feature doesn't automatically update the version badge in README.md due to pattern matching constraints.

**Manual Process**:

1. When Release Please creates a release PR for v1.1.0
2. Manually update README.md:
   ```diff
   - ![Version](https://img.shields.io/badge/version-X.Y.Z-orange)
   + ![Version](https://img.shields.io/badge/version-1.1.0-orange)
   ```
3. Commit with:
   ```bash
   git add README.md
   git commit -m "chore: update README version badge to X.Y.Z"
   git push
   ```
4. The release PR will automatically update to include this change

### Why Not Automatic?

Release Please's generic updater looks for specific patterns:
- `"version": "1.1.0"` (JSON)
- `version = "1.1.0"` (TOML)
- `__version__ = "1.1.0"` (Python)

Our badge format (`https://img.shields.io/badge/version-1.1.0-orange`) doesn't match these patterns.

## ⚠️ **CRITICAL: Version Control Flow**

### The Single Source of Truth

**`.release-please-manifest.json` is the ONLY source of truth for versioning.**

```
┌─────────────────────────────────────┐
│  .release-please-manifest.json      │  ← Truth Source
│  { ".": "1.1.0" }                   │
└────────────┬────────────────────────┘
             │
             ├─→ Analyze commits (feat/fix)
             │
             ├─→ Calculate next version (based on 1.1.0)
             │
             ├─→ Update CHANGELOG.md
             │
             ├─→ Update manifest → "1.1.0"
             │
             └─→ (Manual) Update README.md
```

### ⛔ IMPORTANT: README Updates Do NOT Affect Versioning

**Q: If I manually update README to 1.1.0, will Release Please use 1.1.0 next?**

**A: NO! Release Please completely ignores README versions.**

Example:
```bash
# Current state
.release-please-manifest.json: "1.1.0"
README.md: "1.1.0"

# You manually change README
README.md: "1.1.0"  ← This change is IGNORED

# Next release (after `feat:` commit)
Release Please calculates: 1.1.0 + minor = next release version
                                    ↑
                        Based ONLY on manifest.json
```

**Key Points**:
- ✅ Release Please only reads `.release-please-manifest.json`
- ✅ Version calculation: `manifest version + commit type`
- ❌ Release Please does NOT read README versions
- ❌ Manually updating README won't change version logic

### ✅ Correct Version Update Flow

1. **Current Version**: Check `.release-please-manifest.json`
2. **Make Changes**: Commit with `feat:` or `fix:`
3. **Release Please**: Creates PR with calculated version
4. **Manual Step**: Update README in the release PR branch
5. **Merge PR**: All files sync to new version

## 🔄 Future Improvements

### Option 1: CI Script
Add a GitHub Action step to automatically update README badges:

```yaml
# .github/workflows/update-readme-version.yml
name: Update README Version
on:
  pull_request:
    types: [opened, synchronize]
    branches: [main]

jobs:
  update-readme:
    if: startsWith(github.head_ref, 'release-please--branches--')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}
      
      - name: Extract version from PR title
        id: version
        run: |
          VERSION=$(echo "${{ github.event.pull_request.title }}" | grep -oP '\d+\.\d+\.\d+')
          echo "version=$VERSION" >> $GITHUB_OUTPUT
      
      - name: Update README badge
        run: |
          VERSION=${{ steps.version.outputs.version }}
          sed -i "s/version-[0-9.]*-orange/version-$VERSION-orange/g" README.md
      
      - name: Commit changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add README.md
          git commit -m "chore: update README version badge to ${{ steps.version.outputs.version }}" || echo "No changes"
          git push
```

### Option 2: Version File
Create a `version.py` or `__version__.py` file:

```python
# version.py
__version__ = "1.1.0"
```

Then reference it in README using a build step or keep it simple.

### Option 3: Remove README Version
Rely solely on GitHub Releases for version information. Users can check the latest release tag.

## 🐛 Troubleshooting

### Release Please Didn't Create PR

**Problem**: Merged PR but no release PR appeared.

**Causes**:
1. ❌ Used non-release commit type (`refactor:`, `docs:`, etc.)
2. ❌ Workflow didn't trigger (check Actions tab)
3. ❌ Insufficient permissions in workflow

**Solution**:
- Check commit message follows conventional format
- Verify GitHub Actions ran successfully
- Use `feat:` or `fix:` for user-facing changes

### Duplicate Features in Release Notes

**Problem**: Same commit appears multiple times in release notes.

**Causes**:
- Multiple commits with same message
- Squash merge with duplicate messages

**Solution**:
- Use unique commit messages
- Clean up commit history before merging

## 📚 References

- [Release Please Documentation](https://github.com/googleapis/release-please)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
