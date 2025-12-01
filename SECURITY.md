# Security Policy

## Supported Versions

We actively support the following versions of Universal Manga Downloader with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.3.x   | :white_check_mark: |
| 1.2.x   | :white_check_mark: |
| < 1.2   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in Universal Manga Downloader, please report it responsibly.

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, report security issues via:

**Create a private security advisory on GitHub:**
- Go to: https://github.com/lum-muu/universal-manga-downloader/security/advisories
- Click "New draft security advisory"
- Provide detailed information about the vulnerability

### What to Include

Please include as much of the following information as possible:

- Type of vulnerability (e.g., XSS, SQL injection, path traversal, etc.)
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability and how an attacker might exploit it
- Any potential fixes you've identified

### Response Timeline

- **Initial Response**: Within 48 hours of report
- **Vulnerability Assessment**: Within 5 business days
- **Fix Development**: Varies based on severity and complexity
- **Public Disclosure**: After fix is released, or 90 days from report (whichever comes first)

### Security Update Process

1. We acknowledge receipt of your vulnerability report
2. We confirm the vulnerability and determine its severity
3. We develop and test a fix
4. We release a security update
5. We publicly disclose the vulnerability details (with credit to reporter, if desired)

## Security Best Practices

When using Universal Manga Downloader, follow these security best practices:

### For Users

1. **Keep Updated**: Always use the latest version
2. **Verify Sources**: Only download from official repositories
3. **Review Permissions**: Be cautious about download directory permissions
4. **Network Security**: Use HTTPS connections when available
5. **Dependency Management**: Keep Python and dependencies updated

### For Developers

1. **Code Review**: All code changes require review before merging
2. **Dependency Scanning**: Regular security audits via `pip-audit` in CI/CD
3. **Input Validation**: All user inputs must be validated and sanitized
4. **Secrets Management**: Never commit credentials or API keys
5. **Testing**: Security-related changes must include tests

## Known Security Considerations

### Current Security Measures

- **Input Sanitization**: All filenames and paths are sanitized to prevent path traversal
- **URL Validation**: URLs are validated before making requests
- **Rate Limiting**: API requests are rate-limited to prevent abuse
- **Circuit Breaker**: Fault tolerance patterns prevent cascading failures
- **Dependency Pinning**: Specific dependency versions prevent supply chain attacks
- **Security Scanning**: Automated pip-audit runs in CI/CD pipeline

### Potential Risks

Users should be aware of the following:

1. **Network Requests**: This application makes HTTP requests to manga websites
2. **File System Access**: The application writes files to your designated download directory
3. **Third-Party Dependencies**: Security depends on upstream packages
4. **Cloudflare Bypass**: Uses cloudscraper which may interact with anti-bot measures

## Disclosure Policy

We follow a **Coordinated Vulnerability Disclosure** policy:

- Security researchers are given credit for their findings (unless they prefer anonymity)
- We aim to fix critical vulnerabilities within 30 days
- Details of vulnerabilities are published after fixes are released
- We maintain a security advisory page for all disclosed vulnerabilities

## Security-Related Configuration

### Recommended Python Environment

```bash
# Use virtual environment for isolation
python3 -m venv .venv
source .venv/bin/activate

# Install with pinned dependencies
pip install -r requirements.txt

# Enable pre-commit hooks
pre-commit install
```

### Security Linting

```bash
# Run security checks
bandit -r . -c pyproject.toml

# Audit dependencies
pip-audit -r requirements.txt

# Type checking
mypy manga_downloader.py config.py umd_cli.py core/ plugins/ services/ ui/ utils/
```

## Security Contact

For any security-related questions or concerns:

- **Issues**: https://github.com/lum-muu/universal-manga-downloader/issues (for general security questions)
- **Security Advisories**: https://github.com/lum-muu/universal-manga-downloader/security/advisories (for vulnerability reports)

## Acknowledgments

We appreciate the security research community's efforts in responsibly disclosing vulnerabilities. Contributors who report valid security issues will be acknowledged in:

- The CHANGELOG.md file
- Security advisory publications
- Project documentation (unless anonymity is requested)

## Legal

This project is provided under the CC BY-NC-SA 4.0 license. Users must comply with:

- Applicable copyright laws
- Website terms of service
- Anti-scraping policies
- Data protection regulations

**The maintainers are not responsible for misuse of this software.**
