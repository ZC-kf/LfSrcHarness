# Usage

## Configure authorization scope

Copy `deploy/config/scope.yaml` and edit the target allowlist, time windows, rate limits,
forbidden actions, and privilege flags. Every task is checked by the same policy engine
before execution.

## CLI

```powershell
& '.\.venv\Scripts\lfsrc.exe' --help
& '.\.venv\Scripts\lfsrc.exe' status --database '.\runs\state.sqlite3'
& '.\.venv\Scripts\lfsrc.exe' replay '.\runs\RUN_ID\events.jsonl'
& '.\.venv\Scripts\lfsrc.exe' report '.\runs\RUN_ID'
& '.\.venv\Scripts\lfsrc.exe' stop --task-id 'TASK_ID'
```

`run` and `batch` accept only targets allowed by the selected scope. Actions that require
approval remain paused until an authorized operator approves them through the API or web
console.

## HTTP and web console

Start the API:

```powershell
$env:LFSRC_API_TOKENS_JSON = '{"replace-me":"admin"}'
& '.\.venv\Scripts\uvicorn.exe' 'lfsrc_harness.server:app' --host '127.0.0.1' --port 8619
```

Open `http://127.0.0.1:8619/`. The API uses bearer tokens and roles: viewer, operator,
approver, and admin. Live events use Server-Sent Events.

## AI providers

Provider plugins cover:

- OpenAI-compatible APIs, including compatible domestic gateways and local vLLM/LM Studio;
- Anthropic and Gemini native payloads;
- Ollama local deployment;
- arbitrary local or third-party CLI harnesses.

Secrets are referenced by environment-variable name. A provider configuration must never
contain the secret value itself.

## Agent interfaces

- Python: implement the `AgentAdapter` protocol.
- CLI: exchange one JSON request and JSONL events over standard streams.
- HTTP: send the neutral request schema and receive JSON events.
- gRPC: call `/lfsrc.Agent/Run` with the protobuf `JsonEnvelope`; its `json` field holds
  UTF-8 JSON, and the response JSON contains an `events` array. Send
  `authorization: Bearer <token>` metadata when the server has a configured token. The
  schema reference is `src/lfsrc_harness/proto/lfsrc_harness.proto`.

## Screen, desktop, and browser control

Install the optional automation dependencies with `pip install 'lfsrc-harness[automation]'`
and install Playwright's browser runtime when needed. Control actions still pass through
scope, risk-tier, approval, and emergency-stop checks. Backend absence produces a clear
capability error rather than silently bypassing policy.

## Events and reports

Each run writes a hash-chained JSONL ledger under `runs/RUN_ID/events.jsonl`. Evidence is
content-addressed. Reports can be rendered as Markdown, JSON, HTML, PDF, and SARIF. Use
`lfsrc replay` to validate sequence and hashes before relying on a stored run.
