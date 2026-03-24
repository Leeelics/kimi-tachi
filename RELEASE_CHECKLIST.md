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
- [x] Build successful (python -m build)
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

### 3. Configure Credentials

**Option A: Using .pypirc**
```bash
cat >> ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF
chmod 600 ~/.pypirc
```

**Option B: Using environment variable**
```bash
export PYPI_API_TOKEN="pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## Release Steps

### Step 1: Final Verification
```bash
# Run tests
pytest

# Build package
python -m build

# Check build
ls -la dist/
# Should show:
# - kimi_tachi-0.4.0-py3-none-any.whl
# - kimi_tachi-0.4.0.tar.gz
```

### Step 2: Upload to TestPyPI (Optional but Recommended)
```bash
# Install twine
pip install twine

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ kimi-tachi
```

### Step 3: Upload to PyPI
```bash
# Upload to PyPI
twine upload dist/*

# Or with explicit credentials
twine upload -u __token__ -p $PYPI_API_TOKEN dist/*
```

### Step 4: Verify Release
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

### Step 5: Post-Release
- [ ] Push git tag to remote: `git push origin v0.4.0`
- [ ] Create GitHub Release (optional)
- [ ] Announce on social media (optional)

## Troubleshooting

### Build Errors
```bash
# Clean build artifacts
rm -rf dist/ build/ *.egg-info

# Rebuild
python -m build
```

### Upload Errors
```bash
# Check credentials
twine check dist/*

# Verify PyPI access
twine upload --verbose dist/*
```

### Version Conflicts
```bash
# If version already exists on PyPI, you cannot re-upload
# Must increment version number
```

## Quick Release Command

```bash
# One-liner for future releases
pytest && python -m build && twine upload dist/*
```

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
- tests/ (optional, can be excluded)
- docs/ (optional)
- examples/ (optional)
