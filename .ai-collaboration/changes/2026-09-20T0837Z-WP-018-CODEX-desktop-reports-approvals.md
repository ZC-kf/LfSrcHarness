# WP-018 continuation — desktop reports and approvals

- Writer: Codex (`AI_OWNER: CODEX`), scheme D, protocol 5.1, plan version 8.
- Baseline: `f272f34` plus the existing, unpublished WP-027 local changes.
- Scope: `src/lfsrc_harness/api.py`, `tests/test_api.py`, `web/src/App.tsx`,
  `web/src/App.test.tsx`, `web/src/styles.css`, `docs/DESKTOP_GUIDE.md`,
  `docs/TEST_REPORT.md`, `.ai-collaboration/PROJECT_PLAN.md`, this record,
  and `PROJECT_SUMMARY.md`.
- Requirement: REQ-018. A viewer can list and download an existing run report
  with bearer authentication; a desktop administrator can approve or reject a
  pending approval using the existing API. No task runner was added.
- Implementation: report lookup recognizes the workflow's run-local output
  directory and the previous configured report directory. A single-file route
  rejects invalid names and paths resolving outside the report directory.
  The React view fetches listings only for the selected run, uses the desktop
  bridge token for authenticated downloads, and reports failed requests.
- TDD: the new API test failed at 404 for an existing workflow report; the
  two new frontend tests failed because the buttons and listing did not exist.
- Verification: `pytest -q`: 113 passed, 2 Linux-only skipped; `npm test`:
  7 passed; `npm run build`: exit 0; Ruff and strict mypy: exit 0;
  `git diff --check`: exit 0. A live loopback backend and Playwright loaded
  the compiled UI at 1280x800 and 390x844; report files rendered, the HTML
  download produced the expected filename, and no browser console errors
  occurred. The mobile report button was adjusted after screenshot review.
- Not accepted as a release: the public `preview.3` is unchanged. The desktop
  still has no complete task creation/execution flow; WP-027 clean-machine
  missing-component installation, WP-028 Linux provisioning, and WP-029
  audited Agent distribution remain unverified/incomplete. No external target
  was contacted; the UI fixture used `local-node` on loopback only.
