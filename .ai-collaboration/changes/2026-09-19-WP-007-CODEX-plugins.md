# WP-007 Change Record

- Modifier: Codex
- Scope: plugin transports, registry, examples and interactive-control plugins
- Reason: isolate tools and computer/browser capabilities behind one auditable extension boundary
- Implementation: Python entry points, subprocess/HTTP/gRPC/Docker adapters, tool catalog/template, and policy-gated screen/desktop/browser backends
- Requirements: REQ-007 plus approved interactive-control extension
- Verification: accumulated suite — 48 passed; all interaction tests use fake backends
- Remaining: AI providers and Agent adapters in WP-008
