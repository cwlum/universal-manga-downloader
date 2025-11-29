# UMD Plugin Submission Guide

1. **Clone the Repo**
   ```bash
   git clone https://github.com/umd-plugins/official.git
   cd official
   ```
2. **Create Your Plugin**
   - Parsers → `parsers/your_plugin.py`
   - Converters → `converters/your_plugin.py`
   - Include the metadata docstring block (Name/Author/Version/etc.).
3. **Validate**
   ```bash
   python scripts/validate_plugin.py parsers/your_plugin.py
   ```
4. **Open a PR** using the `[Plugin] Add YourPluginName` template.
5. **Respond to CI Feedback** and reviewers.

## Metadata Tips
- Keep descriptions short (≤140 chars).
- List dependencies with semver specifiers.
- Provide project links (GitHub repo, docs).

## Security Checklist
- No calls to `exec`, `eval`, or system shells.
- Network requests should use UMD services layer, not direct requests inside plugins.
- All file writes must go through the provided `output_dir`.
