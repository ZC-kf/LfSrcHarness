# WP-030 — supplied starfield desktop theme

- Writer: Codex (`AI_OWNER: CODEX`), scheme D, protocol 5.1, plan version 9.
- Baseline: `f272f34` with the preserved, unpublished WP-027 and WP-018
  working-tree changes. No upstream Agent files were edited.
- Scope: `web/public/starfield.png`, `web/public/lfsrc-icon.png`,
  `web/src/styles.css`, `web/src/App.tsx`, `tests/test_theme_assets.py`,
  `docs/ASSUMPTIONS.md`, `docs/CHANGELOG.md`, `docs/DESKTOP_GUIDE.md`, `docs/TEST_REPORT.md`,
  `.ai-collaboration/PROJECT_PLAN.md`, this record and `PROJECT_SUMMARY.md`.
- Requirement mapping: REQ-030 / WP-030 / AC-030. The user-supplied starfield
  is the program background; the existing sword/triangle icon is retained.
- Decision: copy the original PNG unchanged rather than synthesize or alter it.
  Use purple/blue translucent interface chrome with green/amber/red reserved
  for meaningful operational states. Keep the existing layout and controls.
- TDD: two asset/theme tests failed before the copy and CSS/brand change,
  then passed afterward. Source image SHA-256 and packaged image SHA-256 both
  equal `6B23D3CB29F0ADD1739E632B215C6811B8697EF47B437A59A4F751B0CC430A6E`.
- Verification: frontend production build exited 0; live Playwright compiled
  UI showed the supplied background and icon at 1280×800, 1672×941 and
  390×844, with no console errors; report download still worked. Isolated
  PyInstaller build exited 0, frozen `--self-test` exited 0, both visual
  assets were present in the bundle. Final regression: 115 Python tests passed,
  2 Linux-only skipped, 7 frontend tests passed, Ruff and strict mypy passed.
  Full regression/status evidence is in
  `docs/TEST_REPORT.md`.
- Remaining: no new public Release or clean-machine installer test; the Agent
  distribution/execution and official-component gates remain open. The asset
  ownership/redistribution assumption is recorded in `docs/ASSUMPTIONS.md`.
