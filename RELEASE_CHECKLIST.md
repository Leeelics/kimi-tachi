# PyPI Release Checklist

## Pre-Release Checks

### 1. Version Update
- [x] `pyproject.toml` version updated to 0.4.0
- [x] `src/kimi_tachi/__init__.py` __version__ updated to 0.4.0
- [x] README.md version badge updated

### 2. Documentation
- [x] README.md updated with v0.4.0 features
- [x] CHANGELOG.md created with version history
- [x] INSTALL.md created with installation instructions

### 3. Code Quality
- [x] All tests pass (61 tests)
- [x] No linting errors (ruff)
- [x] Type checking passed (optional)

### 4. Build Verification
- [x] Clean dist/ directory
- [x] Build successful (`uv build` or `python -m build`)
- [x] Wheel contains all necessary files
- [x] Version in wheel is correct (0.4.0)

### 5. Git State
- [x] All changes committed
- [x] Git tag v0.4.0 created
- [x] No uncommitted changes

## PyPI Account Setup (One-time)

### 1. Create PyPI Account
1. Go to https://pypi.org/
2. Register for an account
3. Enable 2FA (recommended)

### 2. Create API Token
1. Go to https://pypi.org/manage/account/token/
2. Create token with scope: "Entire account (all projects)"
3. Save token securely (will only be shown once)

## Release Steps

### Step 1: Final Verification
```bash
# Run tests
pytest

# Build package
uv build

# Check build
ls -la dist/
# Should show:
# - kimi_tachi-0.4.0-py3-none-any.whl
# - kimi_tachi-0.4.0.tar.gz
```

### Step 2: Upload to PyPI using uv

**Option A: Using environment variable (Recommended)**
```bash
# Set token as environment variable
export UV_PUBLISH_TOKEN="pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Publish
uv publish
```

**Option B: Using command line argument**
```bash
uv publish --token "pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**Option C: Using username/password (legacy)**
```bash
uv publish --username __token__ --password "pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### Step 3: Verify Release
```bash
# Wait a few minutes for PyPI to update

# Check PyPI page
open https://pypi.org/project/kimi-tachi/0.4.0/

# Test installation
pip install kimi-tachi==0.4.0

# Verify version
kimi-tachi --version
# Should show: kimi-tachi version 0.4.0
```

### Step 4: Post-Release
- [ ] Push git tag to remote: `git push origin v0.4.0`
- [ ] Create GitHub Release (optional)
- [ ] Announce on social media (optional)

## Alternative: Using twine (legacy)

If you prefer using `twine`:

```bash
# Install twine
pip install twine

# Upload to PyPI
twine upload dist/*
```

But `uv publish` is recommended as it's faster and integrated with uv workflow.

## Troubleshooting

### Build Errors
```bash
# Clean build artifacts
rm -rf dist/ build/ *.egg-info

# Rebuild
uv build
```

### Upload Errors
```bash
# Dry run to check without uploading
uv publish --dry-run

# Check if package already exists
# (uv will skip duplicates by default)
```

### Authentication Errors
```bash
# Verify token is set correctly
echo $UV_PUBLISH_TOKEN

# Or use --token flag directly
uv publish --token "your-token-here"
```

### Version Conflicts
```bash
# If version already exists on PyPI, you cannot re-upload
# Must increment version number in pyproject.toml
```

## Quick Release Command

```bash
# One-liner for future releases
pytest && uv build && uv publish
```

## uv vs twine

| Feature | uv publish | twine |
|---------|-----------|-------|
| Speed | ⚡ Fast (Rust) | 🐌 Slower (Python) |
| Integration | Native with uv | Separate tool |
| Dependencies | None extra | Requires install |
| Recommended | ✅ Yes | Legacy |

## Files to Include in Distribution

### Source Distribution (tar.gz)
- All Python source files
- Agent YAML files (agents/)
- README.md, LICENSE, CHANGELOG.md
- pyproject.toml

### Wheel (whl)
- Compiled Python bytecode
- All source files
- Metadata

### Files NOT to Include
- __pycache__/
- *.pyc
- .git/
- tests/ (optional)
- docs/ (optional)
- examples/ (optional)
