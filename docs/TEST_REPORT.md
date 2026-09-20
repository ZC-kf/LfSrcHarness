# Test Report

Date: 2026-09-20

## Public beta preview.4 candidate — desktop local task loop (2026-09-20)

- A regression first showed the desktop task was queued without a local worker.
  The implementation now accepts an in-scope built-in diagnostic task from the
  UI, processes it through policy/orchestration, persists a terminal status,
  and exposes `run_start`, `tool_call`, `tool_result`, `run_end` JSONL events.
  Unknown plugins are rejected; a pre-existing invalid queued task fails
  visibly without blocking later tasks. A changed scope is enforced by the
  running worker. The diagnostic plugin does not contact a target.
- Local Windows suite: **116 Python tests passed, 2 Linux-only tests skipped**;
  **8 frontend tests passed**. Ruff, strict mypy on 26 source files, and
  TypeScript/Vite production build passed. The frozen desktop bundle rebuilt
  from the current source and exited 0 on `--self-test`; its starfield asset
  SHA-256 matched the source. Inno Setup 7.1 compiled the preview.4 installer.
- This is a **public beta**, not a complete Agent acceptance. On this host the
  official-component preflight reports Nmap and Metasploit absent. Installing
  them from the new setup, a clean Windows missing-.NET/WebView2 scenario,
  and a full Kali/Ubuntu installation have not been tested. The original Agent
  is not in the public bundle. No external model or target was contacted.

## Unpublished starfield desktop theme (2026-09-20)

- The supplied 1672×941 PNG was copied byte-for-byte into `web/public`;
  SHA-256 `6B23D3CB29F0ADD1739E632B215C6811B8697EF47B437A59A4F751B0CC430A6E`.
- The purple/blue theme, original sword/triangle icon, desktop report workflow,
  and responsive 1280×800, native 1672×941, and 390×844 screens were inspected
  through the built app. Both visual assets returned HTTP 200; the report
  download completed and browser console errors were empty.
- A fresh PyInstaller bundle built in an isolated temporary folder. Its
  `LfSrcHarness.exe --self-test` exited 0, and the bundled background matched
  the source image's SHA-256. This is not an installer or clean-machine test.
- Final local regression: 115 Python tests passed, 2 Linux-only tests skipped;
  7 frontend tests passed; Ruff, strict mypy, Vite build and `git diff --check`
  passed. Two upstream TestClient deprecation warnings remain.

## Unpublished desktop report/approval continuation (2026-09-20)

- Windows local suite: 113 Python tests passed, 2 Linux-only tests skipped;
  7 React tests passed. Ruff, strict mypy and TypeScript/Vite build passed.
- An authenticated live loopback API returned a generated five-format fixture
  report; Playwright loaded the compiled UI at 1280×800 and 390×844,
  displayed the report list and downloaded its HTML file. Browser console:
  no errors. Approval action is covered by frontend and API tests, not by a
  seeded live UI run.
- This is not a complete-install acceptance test. No Agent bundle, actual
  third-party installer missing-component path, Linux full install or external
  model provider was validated here. The public Release remains preview.3.

## Windows repair preview.3 (2026-09-19)

- Red/green regression reproduced the exact Uvicorn formatter failure with
  `sys.stdout=None` and `sys.stderr=None`; the repaired startup and expanded
  `--self-test` tests passed.
- Local Python suite: 108 passed, 2 Linux-only tests skipped on Windows.
- PyInstaller windowed EXE `--self-test` exited 0; normal launch remained alive
  after five seconds, and its live loopback `/health` returned `ok`. Inno Setup
  7.1 compiled the 35.1 MB installer.
- Disposable-folder install exited 0, both program/UI payload files existed,
  installed EXE self-test exited 0, and normal installed app remained running.
  Deleting the disposable UI entry point and rerunning setup restored it; both
  disposable installations were uninstalled successfully.
- EXE and setup files both expose an embedded icon. Missing-.NET/WebView2
  download flows still require a clean Windows environment for live validation.
- Public GitHub Actions [main run #7](https://github.com/ZC-kf/LfSrcHarness/actions/runs/35452679582)
  and [tag run #8](https://github.com/ZC-kf/LfSrcHarness/actions/runs/35452693646)
  completed successfully. The GitHub Release exposed all three expected
  assets; a fresh public installer download was byte-identical by SHA-256
  to the locally installed/tested installer.

## Automated results

- Python: 88 tests passed on CPython 3.12.13.
- Branch coverage: 82.25% (required minimum: 80%).
- Static checks: Ruff passed; strict mypy passed for 24 source files.
- Frontend: Vitest passed; TypeScript and Vite production build passed.
- Dependency audit: `npm audit --audit-level=high` reported 0 vulnerabilities.
- Deployment: Docker Compose rendering, Bash syntax, and PowerShell syntax passed.
- Container smoke: locked-dependency image built; CLI, HTTP health and authenticated API,
  gRPC with valid bearer metadata, and gRPC rejection without a token were exercised
  against actual containers.
- Compose smoke: API, gRPC, Celery worker, Redis, and PostgreSQL all reached `healthy`;
  the web console returned HTTP 200 and the worker returned a Celery `pong`. The dedicated
  smoke project and its two temporary data volumes were removed after verification.
- Generated evidence: `tests/reports/junit.xml`, `tests/reports/coverage.xml`, and
  `tests/reports/htmlcov/`.

## Scope

Tests cover scope enforcement, risk policy and approvals, emergency stops, runners,
event replay and integrity, scoring, multi-format reports, plugin adapters, AI providers,
computer-control policy gates, orchestration, CLI, HTTP API, gRPC, workflow recovery,
deployment manifests, the React console, and the bundled Agent display integration.

All execution tests use loopback services, mocks, or local fixture processes. No external
assessment target is contacted by the test suite.

## Known warnings

FastAPI's test client currently emits two upstream deprecation warnings involving the
Starlette/httpx compatibility layer. They do not affect the passing results.

The privileged Compose profile, live external AI vendors, commercial tool servers, and
production desktop/browser automation were not exercised by the local smoke suite.

## Desktop installer preview update (2026-09-19)

- 98 Python tests passed; 1 Linux-only installer test was skipped on Windows.
- 5 frontend tests, TypeScript/Vite build, Ruff and strict mypy passed.
- Rebuilt frozen EXE `--self-test`, disposable-folder installation, installed EXE
  `--self-test`, desktop shortcut creation and uninstall all passed.
- WSL Bash syntax and missing-Python preflight passed. Missing-.NET/WebView2 and full
  Kali/Ubuntu installation still require clean-environment validation.

## Public repository and desktop guide update (2026-09-19)

- Current local Python suite: 104 passed, 2 Linux-only tests skipped on Windows;
  branch-aware coverage 81.19% (80% minimum).
- GitHub Actions run [#3](https://github.com/ZC-kf/LfSrcHarness/actions/runs/35433723873)
  for commit `322434f` completed successfully, including container smoke after
  changing the Compose runtime-data mount to a managed volume.
- Chinese desktop guide link and content checks: 2 passed locally. GitHub
  rendered the guide at `main` and in tag `v0.1.1-preview.2`.
- GitHub Actions [run #4](https://github.com/ZC-kf/LfSrcHarness/actions/runs/35433939393)
  passed all jobs for the guide commit. The follow-up pre-release contains the
  corrected source archive; its public download matched SHA-256. The unchanged
  Windows installer asset also matched the local digest displayed by GitHub.
