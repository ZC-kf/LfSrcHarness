# Assumptions

Date: 2026-09-19

- All assessments are performed only against assets the operator is authorized to test.
- The supplied Hacker Agent remains a local upstream bundle. Its adapted dashboard UI
  is part of Harness source, but the copied Agent bundle is excluded from public Git and
  release archives. The upstream Agent is not modified.
- Python 3.12 is authoritative even when another Python version is the machine default.
- Celery plus Redis is the distributed scheduler; local development can use eager/in-process execution.
- SQLite is the implemented MVP task database. Compose provisions PostgreSQL for future
  production migration, but this release does not yet persist tasks in PostgreSQL.
- SSE is the default live-event protocol for the web UI; WebSocket is not required for v1.
- ReportLab provides PDF output to avoid native rendering dependencies.
- Tool adapters describe common security tools but tests use fixtures/mocks and loopback-only harmless commands.
- Burp and Metasploit integrations are transport adapters; commercial licenses, servers and operator authorization are external prerequisites.
- Privileged container, host-network and Docker-socket modes are available only through explicit scope permission plus policy approval.
- K8s support is included as a baseline manifest; cluster-specific ingress, storage classes and secret managers remain deployment choices.
- PyInstaller output is attempted on Windows; source and container distributions are mandatory.
- Package artifacts do not embed runtime secrets, tokens, cookies or private keys.
- Screen, desktop and browser control are optional local-node capabilities and are never silently enabled by installing the core package.
- The bundled Agent dashboard update is presentation-only; Harness APIs and persisted state remain the source of truth.
- “Support all AI” means the platform is provider-neutral and extensible: common protocols receive built-in adapters, while vendor-specific differences are isolated in plugins rather than hard-coded into the core.
- OpenAI-compatible configuration is sufficient for many domestic, international and self-hosted services; native adapters are used where their wire protocols differ.
- Windows desktop distribution does not include model weights. Users configure vendor APIs, relay gateways, or local model endpoints and optional API keys inside the application.
- The original Harness code is intended for noncommercial lawful use; third-party components retain their own licenses. A public repository must not label the whole bundle Apache-2.0 or OSI open source.
- Windows desktop installer checks 64-bit Windows, .NET Framework 4.6.2+ and WebView2. Missing components are downloaded from Microsoft and Authenticode-verified before execution; setup resumes only after successful rechecks. Python and the compiled UI are bundled.
- Public GitHub distribution contains only original Harness source. Optional security tools are acquired separately by the operator from official publisher sites; their licenses and installation are not implied by plugin support.
