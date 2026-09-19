# WP-009 Change Record

- Modifier: Codex
- Scope: persistent orchestration, Celery queue, budgets, concurrency, recovery and resume
- Reason: support unattended distributed execution with bounded cost and recoverable state
- Implementation: SQLite task repository, P0/P1/P2 claims, Celery/Redis factory, target/tool/node limits, resource budgets, replacement-plugin recovery and stop-aware orchestration
- Requirements: REQ-009
- Verification: accumulated suite — 63 passed, including reopen/resume and recovery
- Remaining: PostgreSQL deployment URL is wired in WP-014; SQLite remains the local runtime store
