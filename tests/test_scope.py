from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lfsrc_harness.scope import ScopeConfig, ScopeViolation, load_scope


def valid_scope_data() -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "name": "authorized-lab",
        "tenant_id": "default",
        "targets": ["example.test", "*.lab.example.test", "10.20.0.0/24"],
        "time_windows": [
            {
                "start": (now - timedelta(minutes=5)).isoformat(),
                "end": (now + timedelta(minutes=5)).isoformat(),
            }
        ],
        "rate_limit": {"requests": 20, "per_seconds": 60},
        "prohibited_actions": ["destructive", "persistence"],
        "privileges": {
            "allow_privileged_container": False,
            "allow_host_network": False,
            "allow_docker_socket": False,
        },
    }


def test_scope_validates_and_matches_exact_wildcard_cidr_and_url() -> None:
    scope = ScopeConfig.model_validate(valid_scope_data())

    assert scope.is_target_allowed("example.test")
    assert scope.is_target_allowed("https://api.lab.example.test/path")
    assert scope.is_target_allowed("10.20.0.42")
    assert not scope.is_target_allowed("example.com")
    assert not scope.is_target_allowed("lab.example.test.evil.test")
    assert scope.is_active()


def test_scope_requires_at_least_one_target() -> None:
    data = valid_scope_data()
    data["targets"] = []

    with pytest.raises(ValidationError):
        ScopeConfig.model_validate(data)


@pytest.mark.parametrize("field", ["requests", "per_seconds"])
def test_rate_limit_values_must_be_positive(field: str) -> None:
    data = valid_scope_data()
    data["rate_limit"][field] = 0  # type: ignore[index]

    with pytest.raises(ValidationError):
        ScopeConfig.model_validate(data)


def test_time_window_end_must_follow_start() -> None:
    data = valid_scope_data()
    window = data["time_windows"][0]  # type: ignore[index]
    window["end"] = window["start"]  # type: ignore[index]

    with pytest.raises(ValidationError):
        ScopeConfig.model_validate(data)


def test_assert_target_and_active_window_raise_scope_violation() -> None:
    data = valid_scope_data()
    now = datetime.now(UTC)
    data["time_windows"] = [
        {
            "start": (now - timedelta(hours=2)).isoformat(),
            "end": (now - timedelta(hours=1)).isoformat(),
        }
    ]
    scope = ScopeConfig.model_validate(data)

    with pytest.raises(ScopeViolation, match="outside the authorized scope"):
        scope.assert_target("unauthorized.test")
    with pytest.raises(ScopeViolation, match="authorized time window"):
        scope.assert_active(now)


def test_load_scope_reads_yaml(tmp_path) -> None:
    path = tmp_path / "scope.yaml"
    path.write_text(
        """
name: local-lab
targets:
  - 127.0.0.1
time_windows: []
rate_limit:
  requests: 5
  per_seconds: 10
prohibited_actions:
  - destructive
privileges: {}
""".strip(),
        encoding="utf-8",
    )

    scope = load_scope(path)

    assert scope.name == "local-lab"
    assert scope.tenant_id == "default"
    assert scope.is_target_allowed("127.0.0.1")
    assert scope.is_active()
