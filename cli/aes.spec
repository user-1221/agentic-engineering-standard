# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for building the aes CLI as a standalone binary."""

import os

block_cipher = None

# Paths relative to this spec file
cli_dir = os.path.dirname(os.path.abspath(SPEC))
aes_pkg = os.path.join(cli_dir, "aes")

a = Analysis(
    [os.path.join(aes_pkg, "__main__.py")],
    pathex=[cli_dir],
    binaries=[],
    datas=[
        (os.path.join(aes_pkg, "scaffold", "*.jinja"), os.path.join("aes", "scaffold")),
        (os.path.join(aes_pkg, "schemas", "*.json"), os.path.join("aes", "schemas")),
    ],
    hiddenimports=[
        "click",
        "yaml",
        "jsonschema",
        "jinja2",
        "rich",
        "aes.commands.init",
        "aes.commands.validate",
        "aes.commands.inspect",
        "aes.commands.publish",
        "aes.commands.install",
        "aes.commands.sync",
        "aes.commands.status",
        "aes.commands.search",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="aes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
