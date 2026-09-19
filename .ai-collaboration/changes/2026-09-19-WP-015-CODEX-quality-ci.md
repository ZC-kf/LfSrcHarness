# WP-015 - Test, CI, and quality gates

- Modifier: Codex
- Collaboration scheme: D
- Scope: automated tests, coverage artifacts, static checks, frontend validation,
  deployment syntax checks, and GitHub Actions.
- Reason: complete phase 15 acceptance evidence before packaging.
- Implementation: added cross-platform Python CI, frontend CI, deployment validation,
  container smoke configuration, gRPC server tests, structured logging, and OpenTelemetry
  event spans.
- Requirement mapping: stages 4, 8, 15; JSONL plus OpenTelemetry; CLI/HTTP/Python/gRPC;
  unit, integration, replay, regression, and smoke checks.
- Verification: 88 Python tests passed; 82.25% branch coverage; Ruff passed; strict mypy
  passed; Vitest and Vite build passed; npm audit reported zero vulnerabilities; Compose,
  Bash, and PowerShell syntax checks passed. Locked Docker image passed live CLI, HTTP,
  authenticated API, and gRPC smoke checks.
- Remaining: build distributable artifacts and perform package-level smoke verification in
  WP-016.
