from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_compose_has_api_worker_queue_database_and_privileged_profile() -> None:
    compose = yaml.safe_load((ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert {"api", "grpc", "worker", "redis", "postgres", "worker-privileged"} <= set(services)
    assert services["api"]["image"] == "lfsrc-harness:0.1.0"
    assert services["api"]["env_file"] == "${LFSRC_ENV_FILE:-.env}"
    assert services["api"]["ports"] == ["127.0.0.1:8619:8619"]
    assert services["redis"]["ports"] == ["127.0.0.1:6379:6379"]
    assert "8621" in str(services["grpc"]["healthcheck"]["test"])
    assert "inspect ping" in str(services["worker"]["healthcheck"]["test"])
    assert services["grpc"]["ports"] == ["127.0.0.1:8621:8621"]
    assert "LFSRC_GRPC_TOKEN" in services["grpc"]["environment"]
    assert services["worker-privileged"]["profiles"] == ["privileged"]
    assert services["worker-privileged"]["privileged"] is True
    assert services["worker-privileged"]["network_mode"] == "host"
    assert "/var/run/docker.sock:/var/run/docker.sock" in services["worker-privileged"]["volumes"]


def test_deployment_artifacts_are_complete() -> None:
    required = [
        "deploy/Dockerfile",
        "deploy/docker-compose.yml",
        "deploy/ansible/site.yml",
        "deploy/ansible/roles/lfsrc/tasks/main.yml",
        "deploy/Vagrantfile",
        "deploy/systemd/lfsrc-harness.service",
        "deploy/k8s/lfsrc-harness.yaml",
        "deploy/.env.example",
        "deploy/config/config.yaml",
        "deploy/config/scope.yaml",
        "deploy/install.sh",
        "deploy/install.ps1",
    ]

    assert all((ROOT / path).is_file() for path in required)


def test_safe_deployment_defaults_do_not_enable_privilege() -> None:
    compose_text = (ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")
    unit_text = (ROOT / "deploy" / "systemd" / "lfsrc-harness.service").read_text(encoding="utf-8")
    manifest = yaml.safe_load_all(
        (ROOT / "deploy" / "k8s" / "lfsrc-harness.yaml").read_text(encoding="utf-8")
    )
    deployments = [item for item in manifest if item and item.get("kind") == "Deployment"]

    assert 'profiles: ["privileged"]' in compose_text
    assert "NoNewPrivileges=true" in unit_text
    container = deployments[0]["spec"]["template"]["spec"]["containers"][0]
    assert container["securityContext"]["allowPrivilegeEscalation"] is False


def test_docker_build_context_excludes_runtime_data_and_private_config() -> None:
    patterns = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    assert "package/" in patterns
    assert "runs/" in patterns
    assert "deploy/.env" in patterns
    assert "agent_bundle/" in patterns


def test_container_uses_locked_python_dependencies() -> None:
    dockerfile = (ROOT / "deploy" / "Dockerfile").read_text(encoding="utf-8")

    assert "uv:0.12.3" in dockerfile
    assert "uv sync --locked --no-dev --no-editable" in dockerfile
    assert "COPY agent_bundle/" not in dockerfile
