# PROJECT_PLAN — LfSrcHarness

- Status: V1_ACCEPTED_V2_PUBLIC_BETA_PREVIEW4_CANDIDATE
- `PLAN_VERSION: 9` (v1 requirements and acceptance remain historical)
- Scheme: D
- Owner: Codex
- Target: a runnable, scope-controlled, auditable security automation harness bundled with the existing Hacker Agent.

## Requirements and acceptance map

| REQ | Work package | Acceptance criteria | Verification |
|---|---|---|---|
| REQ-000 | WP-000 initialization and Agent bundle | Required tree and docs exist; bundled Agent matches source | V-000 path, count, hash manifest |
| REQ-001 | WP-001 scope configuration | YAML validates targets, windows, limits, prohibited actions | V-001 pytest scope suite |
| REQ-002 | WP-002 policy engine | action tiers, approval gates and emergency stops are enforced | V-002 pytest policy suite |
| REQ-003 | WP-003 runners and sandboxes | isolated workspaces, timeout/retry/circuit breaker, gated Docker privilege profiles | V-003 unit tests with mocked Docker |
| REQ-004 | WP-004 event ledger | canonical JSONL events, evidence hashes, replay and audit | V-004 replay/hash tests |
| REQ-005 | WP-005 scoring | pytest, diff, exact and rule scoring; optional judge contract | V-005 scoring tests |
| REQ-006 | WP-006 reporting | Markdown, JSON, HTML, PDF and SARIF; archive and comparison | V-006 render/schema tests |
| REQ-007 | WP-007 plugins | Python, subprocess, HTTP, gRPC and Docker adapters; provider-neutral AI; screen, desktop and browser control plugins | V-007 contract tests |
| REQ-008 | WP-008 Agent adapters | Python, CLI, HTTP and gRPC access; OpenAI-compatible, Anthropic, Gemini, Ollama and local Harness providers | V-008 adapter tests |
| REQ-009 | WP-009 orchestration | queues, limits, budgets, recovery, persistence, priorities and stop controls | V-009 orchestration tests |
| REQ-010 | WP-010 CLI | run, batch, report, stop, replay, status, plugin and deploy | V-010 Typer tests |
| REQ-011 | WP-011 API | task/target/run/event/evidence/report/approval/stop endpoints with token RBAC | V-011 API tests |
| REQ-012 | WP-012 Web UI | Harness console plus bundled Agent dashboard refresh: tasks, runs, stream, evidence, reports, approvals, providers, nodes and settings | V-012 npm tests/build |
| REQ-013 | WP-013 automated workflow | authorized discovery through cleanup with checkpoints and recovery | V-013 state-machine tests |
| REQ-014 | WP-014 deployment | Compose, Ansible, Vagrant, systemd, K8s and installers | V-014 syntax/config validation |
| REQ-015 | WP-015 tests and CI | unit, integration, replay, regression and smoke CI | V-015 full suites and coverage |
| REQ-016 | WP-016 packaging | source tarball, Docker image, executable, docs and checksums | V-016 image/EXE smoke and checksum verification |

## Guardrails

- Every execution is denied unless it matches an explicit scope document.
- High-risk and privileged actions require policy approval; privilege is never the default.
- Tests do not probe public or third-party targets and do not start privileged containers.
- All state-changing tool calls emit auditable events; secrets are redacted.
- Each work package receives an independent change record and verification evidence.

## Execution order

WP-000 through WP-016 run sequentially. A work package advances only after its listed verification passes. Regressions return to the owning work package.

## Version 2 desktop and open source distribution

The user's correction supersedes the earlier assumption that a CLI executable plus a browser
console is sufficient as a Windows product. The Windows deliverable must be a real local desktop
application: it opens from a desktop shortcut, bundles its core backend and UI, and exposes
provider keys, local model endpoints, scope, tasks, approvals, reports, logs, and diagnostics
through its interface without asking operators to edit configuration files. Docker remains an
optional advanced execution backend, not a prerequisite for opening the core application.

| REQ | Work package | Acceptance criteria | Verification |
|---|---|---|---|
| REQ-017 | WP-017 desktop runtime | Windows application starts the local Harness backend and embedded UI from a user-selected install directory; no preinstalled Python or Docker required for the core window | V-017 desktop startup, health and frozen-app smoke |
| REQ-018 | WP-018 in-app configuration | Provider endpoints and optional API keys, authorization scope, tasks, approvals, reports and diagnostics are managed in UI; secrets never returned by read APIs or written to project configs | V-018 backend and frontend settings tests, secret-redaction tests |
| REQ-019 | WP-019 installer and updates | Windows graphical installer checks architecture, .NET Framework and WebView2 before installing, guides and fetches missing Microsoft runtimes, then resumes; installs into the selected folder and creates a desktop shortcut. Linux/Kali CLI installer checks prerequisites, verifies assets and supports a selected prefix | V-019 preflight tests, Windows install/launch/rollback smoke, shell syntax |
| REQ-020 | WP-020 public source-available repository | An independent public GitHub repository contains only original Harness source, README, noncommercial license, third-party notices, contribution/security docs, CI, and tagged Release assets; excludes the local Agent bundle, third-party tools, secrets, generated runtime data and oversized binaries | V-020 staged-file/secret audit, clean clone, GitHub URL and release download smoke |
| REQ-021 | WP-021 desktop guide | A Chinese Markdown guide in the repository explains desktop install, first-run model/scope configuration, limitations and troubleshooting without claiming unfinished UI features | V-021 guide link/content tests and published GitHub page |

The user superseded the offline-weights requirement: the installer does not need model
weights. Cloud vendors, local model gateways, and relay services must all accept optional
API keys in the application. The canceled partial download was moved to the Recycle Bin.

All WP-017 through WP-020 use `PROTOCOL_VERSION: 5.1`, `COLLABORATION_SCHEME: D`,
`PLAN_VERSION: 5`, `AI_OWNER: CODEX`, `MODEL_ID: CODEX_NATIVE`,
`REASONING_DEPTH: ADAPTIVE`, and the single worktree at
`H:\Hacker SRC\Hacker SRC Agent\LfSrcHarness`. Write scopes are the files listed in each
work package's independent change record; `READ_ONLY_REVIEWER: NONE`. Publishing remains
gated by third-party redistribution and license review. The target is the new public
repository `ZC-kf/LfSrcHarness`, with its own independent `main` and release history;
the original Agent repository and its `main` branch are out of write scope.
The user approved source-only publication: third-party runtimes/tools are obtained from
their official publishers or operating-system repositories; none of the local
`agent_bundle/` content is redistributed in this repository.

## Version 3 repository presentation and installer discovery

| REQ | Work package | Acceptance criteria | Verification |
|---|---|---|---|
| REQ-022 | WP-022 repository About and download entry | GitHub About uses the user-selected name “凛枫SRC Harness” with an accurate Agent/Harness introduction and links to the current Release; the first screen of README links directly to the Windows installer, source archive, checksum file, and Linux/Kali/Ubuntu/Debian install commands, while stating that no DEB/RPM installer exists | V-022 local Markdown/link checks, public GitHub About/README inspection, Release asset links |

`PROTOCOL_VERSION: 5.1`; `COLLABORATION_SCHEME: D`; `PLAN_VERSION: 6`;
`AI_OWNER: CODEX`; `MODEL_ID: CODEX_NATIVE`;
`REASONING_DEPTH: ADAPTIVE`; `WORKTREE: H:\Hacker SRC\Hacker SRC Agent\LfSrcHarness`;
`READ_ONLY_REVIEWER: NONE`. WP-022 is limited to repository presentation,
installation documentation, project records, and GitHub About metadata. It does
not alter the installer binary, Agent bundle, product runtime, or user-provided icon.

## Version 4 Windows repair and icon integration

The user's newer request supersedes WP-022's no-installer/no-icon limit. Interpret
“missing files” as both the required application payload and documented Windows
prerequisites (.NET Framework and WebView2); do not fetch arbitrary application
files or third-party tools from unverified sources. Keep the original user image
unchanged and derive an installable icon asset from it. The user's latest visual
direction requires the original sword/triangle, a centrally placed head-down
figure with a black face mask, and the green-to-blue 0/1 code background.

| REQ | Work package | Acceptance criteria | Verification |
|---|---|---|---|
| REQ-023 | WP-023 windowed startup repair | A frozen no-console Windows app starts without `sys.stdout`/`sys.stderr`; the existing `--self-test` catches startup configuration failures rather than only API resource failures | V-023 red/green regression, frozen EXE startup smoke |
| REQ-024 | WP-024 installer prerequisite and payload checks | Windows setup detects and offers officially sourced .NET/WebView2 prerequisites before copying, verifies the bundled app payload after installation, and reports a failed check instead of launching a broken app | V-024 installer code/tests, compiled setup, disposable install and negative payload check |
| REQ-025 | WP-025 user icon | The user's `zcarchhk.jpg` remains unchanged; a derived app icon is embedded in the frozen EXE, installer, desktop/Start shortcuts, and window where supported | V-025 asset inspection, EXE resource/icon check, installed shortcut check |
| REQ-026 | WP-026 repaired public preview | A new tagged pre-release contains the repaired Windows installer, updated source/archive and checksums; README/ABOUT direct users to that release; old Release remains available but not the recommended download | V-026 CI, public asset hashes, clean download and launch |

`PROTOCOL_VERSION: 5.1`; `COLLABORATION_SCHEME: D`; `PLAN_VERSION: 7`;
`AI_OWNER: CODEX`; `MODEL_ID: CODEX_NATIVE`; `REASONING_DEPTH: ADAPTIVE`;
`WORKTREE: H:\Hacker SRC\Hacker SRC Agent\LfSrcHarness`;
`READ_ONLY_REVIEWER: NONE`. Write scopes are specified in the independent
WP-023 through WP-026 change records. The original Agent and its repository
remain out of scope.

## Version 5 install-time official components

The user clarified that a selected install folder is preferred, not mandatory: an existing
system installation must be reused, and a vendor installer may require another location
or administrator approval. This supersedes the earlier assumption that every optional
tool must be installed manually after setup. It does not authorize uploading the local
Agent bundle, its private data, or third-party binaries to GitHub.

| REQ | Work package | Acceptance criteria | Verification |
|---|---|---|---|
| REQ-027 | WP-027 Windows official-component preflight | Setup detects existing Nmap and Metasploit Framework installations; absent components are fetched from publisher-controlled URLs into the selected installation's tools/downloads, verified before execution, installed through vendor UI/UAC, then rechecked; failures identify the component and preserve a local log | V-027 PowerShell check-mode tests, Inno compile, separate clean-VM missing-component test before release |
| REQ-028 | WP-028 Linux component provisioning | Kali/Ubuntu/Debian installer reuses existing tools, installs absent supported components from trusted OS/vendor repositories, rechecks and diagnoses unsupported cases | V-028 shell/integration tests on supported distributions |
| REQ-029 | WP-029 audited Agent distribution | Public release contains the publishable first-party Agent required for a complete install, but no private state, secrets, oversized third-party binaries or unreviewed third-party materials | V-029 allowlist and secret/license audit, clean clone, fresh-machine end-to-end acceptance |

`PROTOCOL_VERSION: 5.1`; `COLLABORATION_SCHEME: D`; `PLAN_VERSION: 8`;
`AI_OWNER: CODEX`; `MODEL_ID: CODEX_NATIVE`; `REASONING_DEPTH: ADAPTIVE`;
`WORKTREE: H:\Hacker SRC\Hacker SRC Agent\LfSrcHarness`;
`READ_ONLY_REVIEWER: NONE`. WP-027 is currently the only implementation in progress.
WP-028 and WP-029 are explicitly not accepted. A local Windows setup compile alone is
not evidence of a complete, clean-machine installation or a complete Agent bundle.

## WP-018 continuation — report and approval UI (local, unpublished)

This continues existing REQ-018 without changing the product requirements or plan
version. Scope is the report read/download API, desktop report and approval views,
their tests, and truthful documentation. AC: an authenticated operator can list
and download an existing report; a pending approval exposes approve/reject actions
in the desktop UI; no claim is made that queued tasks execute without a worker.
V: API and React tests, full Python suite, static checks, production frontend
build, and loopback Playwright interaction. Public release remains gated by
WP-027 clean-machine validation, WP-028, WP-029, and complete desktop execution.

## Version 6 supplied starfield theme

The user supplied `art-20260814-233003-264-1bdae646.png` and requested it as
the program background with a matching visual theme. The original file must
remain unchanged. This extends the existing desktop design without changing
the previous sword/triangle app icon.

| REQ | Work package | Acceptance criteria | Verification |
|---|---|---|---|
| REQ-030 | WP-030 supplied background and theme | The original PNG is copied byte-for-byte into the web assets; the desktop UI uses it as the background, shifts its chrome to a readable purple/blue starfield palette, and shows the existing icon | V-030 asset SHA-256/dimensions, frontend tests/build, rendered desktop/native/mobile screenshots, live asset requests |

`PROTOCOL_VERSION: 5.1`; `COLLABORATION_SCHEME: D`; `PLAN_VERSION: 9`;
`AI_OWNER: CODEX`; `MODEL_ID: CODEX_NATIVE`; `REASONING_DEPTH: ADAPTIVE`;
`WORKTREE: H:\Hacker SRC\Hacker SRC Agent\LfSrcHarness`;
`READ_ONLY_REVIEWER: NONE`. WP-030 only changes web assets/theme, their tests,
documentation and collaboration records. It does not authorize releasing the
still-incomplete Agent bundle or bypassing the publication gates above.

## WP-031 desktop task loop (existing REQ-009/018, unpublished)

`PROTOCOL_VERSION: 5.1`; `COLLABORATION_SCHEME: D`; `PLAN_VERSION: 9`;
`AI_OWNER: CODEX`; `MODEL_ID: CODEX_NATIVE`; `REASONING_DEPTH: ADAPTIVE`;
`WORKTREE: H:\Hacker SRC\Hacker SRC Agent\LfSrcHarness`;
`READ_ONLY_REVIEWER: NONE`; `DEPENDENCIES: WP-018, WP-030`.
Write scope: desktop local worker, API plugin catalog/validation, desktop task form,
focused tests, truthful guide/test records and this collaboration archive.
AC-031: the installed desktop can submit an in-scope built-in local diagnostic
task, execute it without Redis/Docker, persist terminal state, expose its JSONL
events, and display status; unknown plugins are rejected before enqueueing.
V-031: red/green desktop/API/React tests, full local suites and static checks,
frozen desktop self-test. This is not an autonomous Agent or public release.
