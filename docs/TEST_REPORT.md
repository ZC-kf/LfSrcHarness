# Test Report

Date: 2026-09-19

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
