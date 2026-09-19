# WP-023 to WP-026 - Windows desktop repair and icon release

- Modifier: Codex; scheme D; baseline `690c58d` on `main` plus the
  in-progress WP-022 documentation edits.
- Requirements: REQ-023 through REQ-026 in plan version 7.
- Write scope: `src/lfsrc_harness/desktop.py`, `tests/test_desktop.py`,
  `deploy/windows/LfSrcHarness.iss`, `tests/test_installer.py`,
  `build/lfsrc-desktop.spec`, `deploy/desktop_entry.py` if needed,
  new project-owned icon assets, `README.md`, `docs/INSTALL.md`,
  `docs/DESKTOP_GUIDE.md`, `docs/CHANGELOG.md`, `docs/TEST_REPORT.md`,
  `.ai-collaboration/PROJECT_PLAN.md`, `.ai-collaboration/PROJECT_SUMMARY.md`,
  this record, generated `package/` assets, and GitHub Release/About metadata.
  Original `C:\Users\Lenovo\Pictures\Camera Roll\zcarchhk.jpg` is read-only.
- Evidence: user traceback enters `uvicorn.Config` from `desktop.main`; installed
  Uvicorn formatter calls `sys.stdout.isatty()` with `None`. A local Python
  reproduction with `sys.stdout=None` yielded the same exception. Existing
  `--self-test` returns before Uvicorn config construction, so it missed the bug.
  Installer currently checks .NET/WebView2 registry state but does not test the
  installed executable after copying files.
- Approach: fix the desktop logging/config boundary, extend self-test, verify
  installation payload, integrate a derived icon from the supplied image, then
  build and independently test a new pre-release. No scanner or Agent bundle
  redistribution.
- Implementation: `desktop.py` configures Uvicorn without the default console
  formatter and runs that configuration in `--self-test`. The setup checks
  required bundled files at compile time and runs the installed EXE self-test
  after copying. The EXE and setup embed a derived ICO. In response to the
  user's correction, the final square asset preserves the blue sword/triangle,
  central hooded, head-down person with black mask, and green/blue binary field.
  The original JPG was not modified.
- Verification: initial regression tests failed with the user's exact formatter
  exception and the self-test coverage gap, then passed after repair. Full local
  pytest: 108 passed, 2 Linux-only skipped. Frozen `--self-test` exited 0;
  normal frozen app remained running and served live `127.0.0.1` `/health=ok`.
  Inno Setup 7.1 compiled the installer.
  Disposable install, installed self-test/startup, deletion-and-repair of the
  UI entry point, and silent uninstall all passed. EXE/setup icon resources
  were extracted successfully.
- Public verification: tagged `v0.1.1-preview.3` from commit `e0a4362`.
  GitHub Actions runs #7 (main) and #8 (tag) completed successfully. The
  public Release showed the installer digest
  `090f92c1980abb35eb9b7c752b6d1ab7b02fdfa4430107eee71e71ceea8330d1`
  and source archive digest
  `e812ea9441df8001a9b858f5a7e896a6874cc0a0a296781014a2d0b1f9e01d49`;
  a fresh public installer download matched the locally installed/tested file.
- Remaining: clean-Windows missing-.NET/WebView2 branch, complete Linux/Kali
  install, and a visible desktop-window interaction still need separate
  environment-specific verification. No production targets were contacted.
