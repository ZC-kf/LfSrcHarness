# WP-019 - Installation prerequisite checks

- Modifier: Codex; collaboration scheme: D; branch: `codex/lfsrc-harness-v1`.
- Scope: `deploy/windows/LfSrcHarness.iss`, `deploy/install.sh`,
  `tests/test_installer.py`, `docs/INSTALL.md`, preview package files and checksums.
- Reason / REQ: REQ-019 requires selected-folder installation, a desktop shortcut,
  prerequisite checks, guided dependency installation and continuation after recheck.
- Implementation: the Windows installer checks x64, .NET Framework 4.6.2+ and WebView2
  before copying files, embeds Microsoft-signed .NET and WebView2 bootstrappers, waits
  and rechecks, then installs
  bundled Python/UI. Linux/Kali `--check` detects Python 3.12/venv and npm when needed;
  `--install-deps` can use apt packages where available, then rechecks.
- Verification: 98 Python tests passed, 1 Linux-only test skipped on Windows; WSL Bash
  syntax and missing-Python negative preflight passed. Inno compiled successfully.
  Disposable-folder install, installed EXE self-test, shortcut check and uninstall passed.
  Nine package SHA-256 entries were independently rechecked.
- Remaining: missing-.NET/WebView2 branches and a full Kali/Ubuntu install need testing in
  suitable clean environments. Installer EXE is unsigned preview. Older v0.1.0 package
  artifacts were not rebuilt in this work package.
