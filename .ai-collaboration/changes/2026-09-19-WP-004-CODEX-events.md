# WP-004 Change Record

- Modifier: Codex
- Scope: JSONL audit ledger, replay and evidence storage
- Reason: make every run inspectable, replayable and tamper-evident
- Implementation: canonical event types, UTC/sequence validation, SHA-256 hash chain, recursive secret redaction, replay integrity checks and content-addressed evidence
- Requirements: REQ-004
- Verification: accumulated suite — 31 passed, including tamper detection and deduplication
- Remaining: orchestration emits these events in WP-009/WP-013
