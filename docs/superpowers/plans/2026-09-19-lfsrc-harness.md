# LfSrcHarness Implementation Plan

**Goal:** Build and package a production-shaped, authorization-first automation harness around the existing Hacker Agent.

**Architecture:** A Python 3.12 core owns scope, policy, execution, events, persistence, orchestration and reports. FastAPI, Typer, a Python SDK and gRPC expose the same application service. Plugins use a single contract across entry points, subprocess, HTTP, gRPC and Docker. A React/Vite UI consumes the API and SSE stream. Deployment artifacts cover Compose, Linux provisioning, VM, systemd and Kubernetes.

**Method:** Implement WP-000 to WP-016 from `.ai-collaboration/PROJECT_PLAN.md`. For code work, add a failing focused test, run it, implement the minimum behavior, rerun it, then run the accumulated suite. Use CPython 3.12.13. Mock Docker and network transports in unit tests. Package only after clean Python and web builds.

## Work packages

1. WP-000: initialize records/docs/tree, vendor the Agent, initialize Git, validate the copy.
2. WP-001: define scope schema, target matching and time/rate/action constraints.
3. WP-002: implement action classification, approvals and emergency-stop hierarchy.
4. WP-003: implement subprocess/Docker runners, workspaces and resilience controls.
5. WP-004: implement event schema, JSONL ledger, evidence hashes and replay.
6. WP-005: implement deterministic scorers and an optional judge interface.
7. WP-006: implement multi-format reports, archives, uploads and comparisons.
8. WP-007: implement tool and AI-provider plugin contracts/transports and safe example adapters.
9. WP-008: expose Python, CLI, HTTP and gRPC Agent adapters plus built-in cloud/local AI providers.
10. WP-009: implement durable orchestration, concurrency/budget limits and recovery.
11. WP-010: complete the Typer command surface.
12. WP-011: complete FastAPI resources, token authentication and RBAC.
13. WP-012: implement and build the React/Vite operator UI.
14. WP-013: implement the end-to-end authorized security assessment state machine.
15. WP-014: create and validate deployment/install artifacts.
16. WP-015: complete CI, coverage, integration, replay and smoke tests.
17. WP-016: produce distributable artifacts and checksums, then smoke-install them.

The user explicitly approved direct execution. This new repository uses a dedicated `codex/lfsrc-harness-v1` branch rather than modifying an existing main branch.
