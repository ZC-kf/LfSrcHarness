# WP-016 - Packaging and final integration

- Modifier: Codex
- Collaboration scheme: D
- Baseline: WP-000 through WP-015 accepted; working tree on
  `codex/lfsrc-harness-v1` with no unrelated source Agent edits.
- Scope: `deploy/Dockerfile`, `deploy/docker-compose.yml`, `.dockerignore`, gRPC
  authentication and protobuf bindings, package artifacts, installation/usage documentation,
  final tests, and project summary.
- Reason: deliver runnable source, Linux image, Python wheel, Windows CLI, deployment
  instructions, and integrity checks with no runtime credentials embedded.
- Requirement mapping: REQ-008, REQ-014, REQ-015, REQ-016; AC: four Agent interfaces,
  authenticated nonlocal gRPC, locked dependency image, five healthy Compose services,
  package checksums.
- Implementation: generated protobuf binding; gRPC bearer metadata and nonlocal fail-closed
  binding; Compose loopback port defaults and service-specific health checks; pinned uv
  installation against `uv.lock`; source and image archives; PyInstaller CLI.
- Verification: 88 Python tests passed with 82.25% branch coverage; Ruff and strict mypy
  passed; frontend test/build and npm audit passed; Windows EXE `--help` passed; image CLI,
  HTTP health/authenticated API, and authenticated/denied gRPC passed; Compose API, gRPC,
  worker, Redis, and PostgreSQL all healthy, worker `pong`; eight package checksums passed.
- Boundaries: SQLite remains the MVP task store; Postgres is provisioned but not used for
  task persistence. Live vendors, production desktop/browser automation, and privileged
  profile were not exercised by fixture/local smoke tests.
- Cleanup: isolated `lfsrc-smoke-20260919` containers, network, and two test volumes were
  removed. The built Docker image and package artifacts remain.
