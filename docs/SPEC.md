# LfSrcHarness Specification

## Purpose

LfSrcHarness coordinates an AI security-assessment Agent for explicitly authorized targets. It validates scope before work, classifies every action, gates high-risk operations, executes tools through controlled runners, records an immutable-style JSONL audit stream, evaluates results, and produces reusable reports.

## Functional requirements

- Load and validate YAML scope including target allowlists, time windows, rate limits, prohibited actions and privileged-mode permissions.
- Apply five action tiers: read-only, scan, validation, exploit and high-risk.
- Support pending approvals and global, run and target emergency stops.
- Run subprocess and Docker tools with isolated workspaces, timeouts, retries, exponential backoff, resource limits and circuit breakers.
- Represent events as JSONL: `run_start`, `llm_call`, `tool_call`, `tool_result`, `file_edit`, `finding`, `run_end`.
- Hash evidence and replay event streams deterministically.
- Score runs with tests, file diffs, exact matches and rule assertions; permit an optional external judge.
- Render Markdown, JSON, HTML, PDF and SARIF reports, archive them and compare runs.
- Load plugins through Python entry points and invoke subprocess, HTTP, gRPC and Docker transports.
- Treat AI providers as plugins. Ship provider adapters for OpenAI-compatible APIs, Anthropic, Gemini, Ollama and local CLI/Harness processes; expose a stable contract for any additional domestic, international or self-hosted model.
- Provide policy-gated interactive-control plugins for screen observation, desktop input and browser automation. Every action must be represented as a typed tool call, audited, interruptible and replaceable by an OS/browser-specific backend.
- Expose the Agent through Python, CLI, HTTP and gRPC.
- Orchestrate queued work with priorities, budgets, concurrency limits, persisted checkpoints and bounded recovery.
- Provide Typer CLI, FastAPI service, token/RBAC, SSE event streaming and React/Vite UI.
- Refresh the bundled Agent dashboard as a non-authoritative display surface for Harness status, providers, nodes, approvals, events and report links without moving execution logic into the UI.
- Deploy through Docker Compose, Ansible, Vagrant, systemd and Kubernetes.
- Package source and installation artifacts under `package/`.

## Security invariants

1. No target is actionable unless it matches the active allowlist.
2. A prohibited action always loses to an allow rule.
3. Exploit, high-risk and privileged modes require explicit policy decisions.
4. Docker `privileged`, host networking and Docker-socket mounts are opt-in capabilities, never defaults.
5. Global stop overrides every other state; run stop overrides that run; target stop overrides that target.
6. Credentials and tokens are supplied at runtime and are redacted from events and reports.
7. Evidence is content-addressed and report claims retain evidence references.
8. Provider credentials come only from runtime environment or external secret stores and are redacted from events.
9. Interactive control is disabled until explicitly enabled for the local node; desktop input and browser navigation remain subject to policy and emergency stops.

## Platforms

- Development/runtime: Python 3.12 on Windows or Linux.
- Deployment: Kali, Ubuntu and Debian on VM, bare metal, Docker or Kubernetes.
- Windows paths and generated scripts quote paths containing spaces.

## Definition of done

The Python suite and web build pass, deployment configuration validates, a local harmless smoke task completes through scope-policy-runner-events-report, distributable checksums verify, and `package/` contains installable artifacts and documentation.
