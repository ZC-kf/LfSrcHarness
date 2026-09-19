# PROJECT_PLAN — LfSrcHarness

- Status: V1_ACCEPTED_V2_PUBLIC_PREVIEW_PUBLISHED
- `PLAN_VERSION: 5` (v1 requirements and acceptance remain historical)
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
