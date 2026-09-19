# WP-002 Change Record

- Modifier: Codex
- Scope: action policy, approvals and emergency stops
- Reason: enforce risk tiers and prevent ungated high-risk or privileged execution
- Implementation: five-tier action model, deterministic request fingerprints, thread-safe approvals, deny-first prohibited actions, scope-bound privileges and global/run/target stops
- Requirements: REQ-002
- Verification: accumulated scope/policy suite — 13 passed
- Remaining: approval persistence and API surfaces are completed in WP-009/WP-011
