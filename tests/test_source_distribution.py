import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_public_source_excludes_local_agent_bundle_and_runtime_artifacts() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--cached"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    paths = result.stdout.splitlines()

    assert paths
    assert not any(path.startswith(("agent_bundle/", "package/", "build/tools/")) for path in paths)
    assert not any(path.startswith("runs/") and path != "runs/.gitkeep" for path in paths)
    assert not any(path.endswith((".exe", ".dll", ".sqlite3")) for path in paths)


def test_published_console_includes_core_views() -> None:
    app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")

    for label in ("任务队列", "报告中心", "审批队列", "模型连接", "授权范围"):
        assert label in app
