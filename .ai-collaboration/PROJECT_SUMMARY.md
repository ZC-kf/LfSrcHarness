# LfSrcHarness v0.1.0 project summary

- Date: 2026-09-19
- Protocol: 5.1
- `COLLABORATION_SCHEME: D` (Codex sole code writer and final verifier)
- Plan: REQ/WP-000 through REQ/WP-016 in `PROJECT_PLAN.md`
- Result: accepted functional MVP with source, Docker image, Python wheel, Windows CLI,
  web console, adapted Agent dashboard, deployment assets, tests, and documentation.

## Architecture and decisions

Authorization scope and policy gate actions before execution. Events are hash-chained JSONL
with replay and evidence hashing. Plugins isolate model, tool, and interactive-control
transports. Agent access is available through Python, CLI, HTTP and authenticated gRPC.
Celery/Redis handles distributed scheduling; SQLite is the implemented task store. The
Compose stack provisions PostgreSQL for a future persistence migration, not as the current
task repository. Docker privilege mode is separate and opt-in; normal services bind host
ports to loopback.

The copied Agent dashboard is presentation-only. The source Agent at
`H:\Hacker SRC\Hacker SRC Agent\Hacker` was not edited. Private runtime config files were
omitted from the copied bundle; only examples remain.

## 0.1.1 desktop preview extension

The Windows desktop preview now embeds the backend and React UI, manages provider
endpoints/optional API keys and scope in-app, and ships a graphical installer. The
installer checks x64, .NET Framework 4.6.2+ and WebView2, offers Microsoft-signed
bootstrapper installers
when needed, then continues after a successful recheck. Linux/Kali installation has a
prerequisite check and optional apt-based dependency installation. No model weights are
bundled. `ZC-kf/LfSrcHarness` is the planned independent public repository; the original
Agent repository and its `main` remain untouched. Publication is not yet complete.

Desktop preview verification: 98 Python tests passed, 1 Linux-only test skipped on
Windows; 5 React tests, Vite build, Ruff and strict mypy passed. Frozen EXE self-test,
selected-folder install, installed EXE self-test, desktop shortcut and uninstall passed.
The missing-.NET/WebView2 flows and full Kali/Ubuntu installation remain untested. The earlier
v0.1.0 wheel, source archive, Docker image and CLI binary are older snapshots, not the
desktop preview. The public repository and Release are pending third-party license,
secret and oversized-asset review.
Original Harness code now names PolyForm Noncommercial 1.0.0; this is source-available,
not OSI open source. A redacted Agent-bundle scan reported 3388 potential secret
findings, chiefly in third-party skills. `agent_bundle/` is locally present but
temporarily Git-ignored; no public push has occurred.

## Verification

- 88 Python tests passed; 82.25% branch coverage.
- Ruff and strict mypy passed; frontend Vitest, TypeScript/Vite build, and npm audit passed.
- Windows standalone executable started successfully.
- Locked Docker image built. Live image CLI, HTTP health/authenticated API and gRPC bearer
  allow/deny behavior passed.
- Compose API, gRPC, worker, Redis, and PostgreSQL reached healthy; worker returned `pong`.
- Source archive exclusion audit found no runtime secrets directory, local environment,
  package recursion, or run data. Eight package checksum entries were independently verified.

See `docs/TEST_REPORT.md` and `package/checksums.txt` for release evidence. The final
artifact directory is `H:\Hacker SRC\Hacker SRC Agent\LfSrcHarness\package`.

## Explicit limits

PostgreSQL task persistence, live external model/vendor interoperability, licensed tool
servers, optional screen/desktop/browser backends on production nodes, and the privileged
Compose profile require later environment-specific validation. Local tests use fixtures and
loopback only. No production target was contacted during acceptance.
