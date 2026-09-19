# Scope format

`scope.yaml` is validated by `lfsrc_harness.scope.ScopeConfig` before a run starts.

- `name`: non-empty authorization label.
- `tenant_id`: tenant boundary, default `default`.
- `targets`: one or more exact hosts, wildcard subdomains, IP addresses or CIDR ranges.
- `time_windows`: optional timezone-aware ISO-8601 start/end pairs; empty means no time restriction.
- `rate_limit`: positive request count and interval seconds.
- `prohibited_actions`: action names that policy must deny.
- `privileges`: three independent opt-ins for privileged containers, host networking and Docker socket access.

The example is `plugins/scope.example.yaml`. Matching occurs on normalized host names or IP addresses; URL paths never expand authorization.
