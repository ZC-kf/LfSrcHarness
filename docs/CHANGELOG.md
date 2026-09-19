# Changelog

## 0.1.1-preview.3 - 2026-09-19

- Fixed the frozen Windows desktop startup failure when no console streams exist
  (`Unable to configure formatter 'default'`). The bundled self-test now covers
  server configuration as well as API and UI resources.
- Added post-install self-test and required-payload checks to the Windows setup;
  rerunning setup restores missing bundled files. Existing .NET/WebView2 preflight
  continues to use Microsoft-signed installers.
- Added a Windows EXE/setup icon derived from the user's original artwork,
  preserving the blue sword/triangle, centrally placed masked figure, and
  green-to-blue binary backdrop.
- Moved direct Windows and Linux/Kali downloads and install commands to the top
  of the repository README.

## 0.1.1-preview.2 - 2026-09-19

- Published a Chinese Windows desktop usage guide with install, model, scope,
  troubleshooting, and preview-limit instructions.
- Fixed the default Docker Compose runtime volume for non-root services.
- Reissued the source archive and checksums; the Windows installer binary is
  unchanged from `0.1.1-preview`.

## 0.1.0 - 2026-09-19

- Added authorization scope validation, action tiers, approval gates, and emergency stops.
- Added subprocess and Docker runners with timeouts, retries, resource controls, and circuit
  breaking.
- Added hash-chained JSONL events, evidence hashing, replay, structured JSON logging, and
  OpenTelemetry event spans.
- Added scoring and Markdown, JSON, HTML, PDF, and SARIF reporting.
- Added Python entry-point, subprocess, HTTP, gRPC, and Docker plugin transports.
- Added model-neutral providers for OpenAI-compatible, Anthropic, Gemini, Ollama, and CLI
  runtimes.
- Added Python, CLI, HTTP, and gRPC Agent adapters.
- Added persistent orchestration, priorities, concurrency and cost budgets, checkpoints,
  recovery, and Celery/Redis scheduling.
- Added Typer CLI, FastAPI/RBAC/SSE API, React operations console, and bundled Agent display
  integration.
- Added Docker Compose, Ansible, Vagrant, systemd, and Kubernetes deployment assets.
- Added cross-platform CI, 88 Python tests, frontend tests, static checks, and coverage
  artifacts.
