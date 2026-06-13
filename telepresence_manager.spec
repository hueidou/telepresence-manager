# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Telepresence Manager."""

import os

base_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(base_dir, 'main.py')],
    pathex=[base_dir],
    binaries=[],
    datas=[
        (os.path.join(base_dir, 'web', 'index.html'), 'web'),
        (os.path.join(base_dir, 'web', 'style.css'), 'web'),
        (os.path.join(base_dir, 'web', 'app.js'), 'web'),
        (os.path.join(base_dir, 'web', 'i18n.js'), 'web'),
        (os.path.join(base_dir, 'VERSION'), '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TelepresenceManager',
    upx=True,
    console=False,
)
