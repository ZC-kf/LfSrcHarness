from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_ci_runs_python_web_deployment_and_package_checks() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    jobs = workflow["jobs"]

    assert {"python", "web", "deployment", "container-smoke"} <= set(jobs)
    rendered = str(workflow)
    for command in ["pytest", "ruff", "npm ci", "npm run build", "docker compose"]:
        assert command in rendered
