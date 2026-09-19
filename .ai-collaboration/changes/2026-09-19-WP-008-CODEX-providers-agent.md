# WP-008 Change Record

- Modifier: Codex
- Scope: cloud/local AI providers and Agent transport adapters
- Reason: support domestic, international and self-hosted AI without coupling the core to one vendor
- Implementation: OpenAI-compatible, Anthropic, Gemini, Ollama and CLI providers; provider registry; Python/CLI/HTTP/gRPC Agent adapters
- Requirements: REQ-008 plus approved provider-neutral extension
- Verification: accumulated suite — 56 passed with mocked HTTP/gRPC and local fixture processes
- Remaining: provider management surfaces in API/UI
