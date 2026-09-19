# WP-021 - Chinese desktop guide

- Modifier: Codex; collaboration scheme: D; branch: `main`.
- Scope: `docs/DESKTOP_GUIDE.md`, `README.md`, `docs/INSTALL.md`,
  `docs/README.md`, `docs/DIRECTORY_TREE.md`, `docs/TEST_REPORT.md`,
  `tests/test_desktop_guide.py`,
  `.ai-collaboration/PROJECT_PLAN.md`, and this record.
- Reason / REQ: REQ-021; the user requested that the desktop usage instructions
  also be maintained as Markdown in the GitHub repository.
- Implementation: document verified Windows installation and first-run flows,
  model endpoint/API-key handling, authorization scope, current preview-page
  limitations, local data, troubleshooting, and noncommercial/security notices.
  Link the guide from root and installation docs. No product functionality changed.
- Verification: `tests/test_desktop_guide.py` passed (2 tests); complete local
  Python suite passed (104 passed, 2 skipped). Published-page check pending.
- Remaining: the missing-prerequisite installation path still needs a clean
  Windows VM test; the guide marks unfinished desktop capabilities explicitly.
