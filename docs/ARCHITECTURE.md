# Architecture

```text
CLI / Python SDK / HTTP API / gRPC
                 |
          Application service
                 |
 Scope -> Policy -> Orchestrator -> Runner -> Plugin transport
                 |                   |
          State repository       Subprocess/Docker/HTTP/gRPC
                 |
        JSONL events + evidence
                 |
        Scoring -> Reporting -> Archive
                 |
        FastAPI/SSE -> React UI
```

## Components

- Pydantic models and enums live next to their owning modules.
- `scope`: scope parsing, time-window evaluation and target matching.
- `policy`: action decisions, approvals and emergency stops.
- `runner`: disposable workspaces and bounded process/container execution.
- `events` and `evidence`: JSONL audit trail, redaction, hashes and replay.
- `scoring`: deterministic evaluators and optional judge boundary.
- `reporting`: normalized finding model and five output formats.
- `plugins`: manifest, registry and transport adapters.
- `providers`: provider-neutral AI contract and plugins for OpenAI-compatible services, Anthropic, Gemini, Ollama and local CLI/Harness processes.
- `computer`: typed screen, desktop and browser actions over injectable backends, with policy checks and audit events around every action.
- `agent`: bundled Hacker Agent adapter and common event conversion.
- `orchestration`: persistent state machine, budgets, concurrency and recovery.
- `api`, `cli`, `grpc`: transport edges over one service layer.
- `web`: operator UI consuming REST and SSE.

## Persistence and queues

SQLite is the implemented task repository for this MVP, including Compose. PostgreSQL is
provisioned by Compose but task persistence has not been migrated to it. Celery and Redis
provide distributed queueing; an in-process backend keeps tests and single-node use
operational.

## Privileged execution

Privilege is a declared execution profile with three independent flags: privileged container, host networking and Docker socket mount. Scope must permit each flag, policy must approve the resulting high-risk action, and the runner records the resolved container configuration before execution. Unit tests validate configuration without starting privileged containers.

## Agent integration

The original Agent stays in the user's local directory and is not part of the public
source distribution. The Harness console provides its own task, provider and approval
views. External Agents connect through the CLI, HTTP, Python or gRPC adapter boundary.

## AI provider compatibility

The core never imports a vendor SDK. Providers implement generation, streaming and health
checks through one contract; the registry lists configured providers. The OpenAI-compatible
adapter covers services and local servers that implement compatible chat endpoints, including
domestic and international gateways, vLLM and LM Studio. Native adapters cover Anthropic,
Gemini and Ollama; CLI adapters cover local Harness-style tools. Provider endpoints and keys
must be configured externally, and live vendor interoperability is not claimed by fixture tests.

## Interactive control

The control layer follows the same boundary as other tools: observe, decide, authorize, execute, record. A screen backend returns image evidence; a desktop backend implements pointer, keyboard and application actions; a browser backend implements navigation, DOM inspection and interaction. Playwright and desktop automation libraries are optional backends, while the core contract remains dependency-neutral and testable with fakes. A node capability flag must enable these plugins, and the global/run/target stop registry can interrupt them.
