# Test Report

Date: 2026-09-19

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
