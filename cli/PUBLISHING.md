# Publishing Checklist

Manual steps for releasing `aes-cli` to PyPI and building standalone binaries.

## Pre-release

1. **Bump version** in `pyproject.toml` (`version = "X.Y.Z"`)
2. **Sync schemas** — copy from repo root into the package:
   ```bash
   cp ../schemas/*.json aes/schemas/
   ```
3. **Run tests**:
   ```bash
   cd cli
   .venv/bin/python -m pytest tests/ -v
   ```
4. **Build and check**:
   ```bash
   rm -rf dist/
   .venv/bin/python -m build
   .venv/bin/python -m twine check dist/*
   ```

## PyPI

### First-time setup

1. Create account at https://pypi.org/account/register/
2. Enable 2FA (required for new projects)
3. Create API token at https://pypi.org/manage/account/token/ (scope: project `aes-cli`)
4. Save token in `~/.pypirc`:
   ```ini
   [pypi]
   username = __token__
   password = pypi-XXXX...
   ```

### Test upload (recommended for first release)

```bash
# Upload to TestPyPI first
.venv/bin/python -m twine upload --repository testpypi dist/*

# Verify install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ aes-cli
aes --help
```

### Production upload

```bash
.venv/bin/python -m twine upload dist/*
```

Verify: `pip install aes-cli && aes --help`

## Standalone Binaries (PyInstaller)

### Local build

```bash
cd cli
pip install pyinstaller
pyinstaller aes.spec

# Test the binary
./dist/aes --help
./dist/aes validate ../examples/ml-pipeline
```

This produces a single `dist/aes` binary for your current OS/arch.

### Cross-platform builds

PyInstaller cannot cross-compile. You must build on each target platform:

| Platform       | Build on           | Output binary |
|----------------|--------------------|---------------|
| macOS arm64    | Apple Silicon Mac  | `aes-macos-arm64` |
| macOS x86_64   | Intel Mac          | `aes-macos-x64` |
| Linux x86_64   | Linux (or Docker)  | `aes-linux-x64` |
| Windows x86_64 | Windows            | `aes-windows-x64.exe` |

### GitHub Actions (future)

To automate cross-platform builds, create `.github/workflows/release.yml`:

```yaml
# Outline — not ready to use as-is
name: Release
on:
  push:
    tags: ["v*"]

jobs:
  pypi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install build twine
      - run: cp schemas/*.json cli/aes/schemas/
      - run: cd cli && python -m build
      - run: cd cli && python -m twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}

  binaries:
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            name: aes-linux-x64
          - os: macos-latest
            name: aes-macos-arm64
          - os: windows-latest
            name: aes-windows-x64.exe
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install pyinstaller
      - run: cd cli && pip install .
      - run: cp schemas/*.json cli/aes/schemas/
      - run: cd cli && pyinstaller aes.spec
      - run: mv cli/dist/aes* ${{ matrix.name }}
      # Upload as release asset (use softprops/action-gh-release or similar)
```

### GitHub Release

After building binaries on each platform:

```bash
gh release create v0.1.0 \
  --title "aes-cli v0.1.0" \
  --notes "First release" \
  aes-macos-arm64 \
  aes-linux-x64 \
  aes-windows-x64.exe
```

## Release checklist (copy-paste)

```
- [ ] Version bumped in pyproject.toml
- [ ] Schemas synced (cp ../schemas/*.json aes/schemas/)
- [ ] Tests pass
- [ ] Built sdist + wheel (python -m build)
- [ ] twine check passes
- [ ] Uploaded to TestPyPI and verified
- [ ] Uploaded to PyPI
- [ ] PyInstaller binary built and tested locally
- [ ] GitHub Release created with binaries (if applicable)
- [ ] Git tag created (git tag v0.X.Y && git push --tags)
```
