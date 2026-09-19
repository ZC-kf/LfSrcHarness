# WP-003 Change Record

- Modifier: Codex
- Scope: subprocess/Docker runners, workspaces and resilience controls
- Reason: provide bounded execution without shell interpolation and with explicit privilege profiles
- Implementation: disposable workspaces, timeout, retries, exponential backoff, circuit breaker, restricted Docker config and SDK runner
- Requirements: REQ-003
- Verification: accumulated suite — 20 passed; container settings tested without starting a privileged container
- Remaining: orchestration integrates policy decisions before runner invocation in WP-009
