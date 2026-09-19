# WP-001 Change Record

- Modifier: Codex
- Scope: scope YAML model and authorization matching
- Reason: make targets, windows, rates, prohibited actions and privileges machine-enforceable
- Implementation: Pydantic models, YAML loader, exact/wildcard/CIDR matching, active-window checks and explicit violations
- Requirements: REQ-001
- Verification: `tests/test_scope.py` — 7 passed
- Remaining: schema export will be exposed through API documentation in WP-011
