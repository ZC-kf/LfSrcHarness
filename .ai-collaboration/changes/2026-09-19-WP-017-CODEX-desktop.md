# WP-017 - Windows desktop runtime

- Modifier: Codex; collaboration scheme: D; branch: `codex/lfsrc-harness-v1`.
- Scope: `src/lfsrc_harness/desktop.py`, `deploy/desktop_entry.py`,
  `build/lfsrc-desktop.spec`, `pyproject.toml`, `uv.lock`, `tests/test_desktop.py`.
- Reason / REQ: REQ-017 requires a real desktop window that bundles the local Harness
  backend and interface without requiring a preinstalled Python or Docker runtime.
- Implementation: pywebview hosts the compiled React UI; an in-process loopback API
  uses an ephemeral admin token. User data is stored in the current user's app data.
- Verification: desktop tests passed within 98 Python tests; the rebuilt frozen EXE
  passed `--self-test`, both before and after disposable-folder installation.
- Remaining: visual desktop interaction and other Windows versions need wider testing.
