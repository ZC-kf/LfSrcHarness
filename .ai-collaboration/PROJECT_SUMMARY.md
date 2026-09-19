# LfSrcHarness project summary through the v0.1.1-preview.3 local build

- Date: 2026-09-19
- Protocol: 5.1
- `COLLABORATION_SCHEME: D` (Codex sole code writer and final verifier)
- Plan: REQ/WP-000 through REQ/WP-021 in `PROJECT_PLAN.md`
- Result: functional MVP plus a public, source-only desktop preview, Windows installer,
  Chinese desktop guide, release assets, and independent CI verification.

## Architecture and decisions

Authorization scope and policy gate actions before execution. Events are hash-chained JSONL
with replay and evidence hashing. Plugins isolate model, tool, and interactive-control
transports. Agent access is available through Python, CLI, HTTP and authenticated gRPC.
Celery/Redis handles distributed scheduling; SQLite is the implemented task store. The
Compose stack provisions PostgreSQL for a future persistence migration, not as the current
task repository. Docker privilege mode is separate and opt-in; normal services bind host
ports to loopback.

The locally copied Agent dashboard is presentation-only. The source Agent at
`H:\Hacker SRC\Hacker SRC Agent\Hacker` was not edited. Private runtime config files were
omitted from the copied bundle; only examples remain. The entire `agent_bundle/`
directory is excluded from the public repository and release source archive.

## 0.1.1 desktop preview extension

The Windows desktop preview now embeds the backend and React UI, manages provider
endpoints/optional API keys and scope in-app, and ships a graphical installer. The
installer checks x64, .NET Framework 4.6.2+ and WebView2, fetches Microsoft-signed
bootstrapper installers when needed, then continues after a successful recheck.
Linux/Kali installation has a prerequisite check and optional apt-based dependency
installation. No model weights are bundled. The independent public repository is
`https://github.com/ZC-kf/LfSrcHarness`; the original Agent repository and its
`main` remain untouched.

The public `v0.1.1-preview.2` pre-release contains the unchanged Windows installer,
updated source archive and SHA-256 checksums. It includes the Chinese desktop guide
and the corrected non-root Docker Compose runtime volume. Its public source download
matched the local digest. Windows installer self-test, selected-folder installation,
shortcut creation and uninstall had passed earlier. Missing-.NET/WebView2 flows and
full Kali/Ubuntu installation remain untested. Desktop task creation, approvals and
report downloads are not complete UI workflows and are labeled as such in the guide.
The earlier v0.1.0 wheel, Docker image and CLI binary remain older local snapshots.
Original Harness code uses PolyForm Noncommercial 1.0.0: source-available, not OSI
open source. Third-party tools, the local Agent bundle, secrets and runtime data
were excluded from the public repository.

## Verification

- 104 Python tests passed locally on Windows; 2 Linux installer tests skipped;
  81.19% branch-aware coverage.
- Ruff and strict mypy passed; frontend Vitest, TypeScript/Vite build, and npm audit passed.
- Windows standalone executable started successfully.
- Locked Docker image built. Live image CLI, HTTP health/authenticated API and gRPC bearer
  allow/deny behavior passed.
- Compose API, gRPC, worker, Redis, and PostgreSQL reached healthy; worker returned `pong`.
- GitHub Actions runs #3 and #4 passed all jobs, including Linux container smoke.
- Tagged source archive excludes the Agent bundle, third-party binaries, secrets and
  runtime data. Public source download and release-asset digests matched local hashes.

See `docs/TEST_REPORT.md` and the Release's
`SHA256SUMS-0.1.1-preview.2.txt` for current preview evidence. The local artifact
directory is `H:\Hacker SRC\Hacker SRC Agent\LfSrcHarness\package`.

## Explicit limits

PostgreSQL task persistence, live external model/vendor interoperability, licensed tool
servers, optional screen/desktop/browser backends on production nodes, and the privileged
Compose profile require later environment-specific validation. Local tests use fixtures and
loopback only. No production target was contacted during acceptance.

## 0.1.1-preview.3 local repair

WP-022 through WP-026 address repository discoverability and a Windows windowed-app
startup failure. A red regression reproduced the reported Uvicorn formatter
exception with absent console streams. The desktop entry now avoids Uvicorn's
console formatter, and its self-test also exercises server configuration.
Windows setup validates embedded program/UI files and executes installed
`--self-test`; rerunning setup restored a deliberately removed UI file in a
disposable installation. The user's original image remains unchanged; the
embedded program/setup icon preserves the sword/triangle, central hooded
masked figure, and green/blue binary field. Local pytest passed 108 tests
with 2 Linux-only skips. Frozen self-test, normal startup, installer compile,
install, repair and uninstall passed on Windows. Clean-OS .NET/WebView2
bootstrapper behavior is unverified. Public GitHub CI/Release are pending.
