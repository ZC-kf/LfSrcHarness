# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

root = Path(SPECPATH).parent
datas = [
    (str(root / "web" / "dist"), "web/dist"),
    (str(root / "deploy" / "config" / "scope.yaml"), "deploy/config"),
]
binaries = []
hiddenimports = collect_submodules("keyring.backends")
for package in ("lfsrc_harness", "webview"):
    package_data, package_binaries, package_hidden = collect_all(package)
    datas += package_data
    binaries += package_binaries
    hiddenimports += package_hidden

analysis = Analysis(
    [str(root / "deploy" / "desktop_entry.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, [], exclude_binaries=True,
    name="LfSrcHarness", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
)
coll = COLLECT(
    exe, analysis.binaries, analysis.datas,
    strip=False, upx=False, name="LfSrcHarness-Desktop-Preview",
)
