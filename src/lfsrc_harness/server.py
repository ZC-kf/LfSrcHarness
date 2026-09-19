"""Deployment entry point for the API and compiled operator console."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from .api import create_app
from .scope import load_scope

PROJECT_ROOT = Path(os.environ.get("LFSRC_ROOT", Path(__file__).parents[2])).resolve()
SCOPE_PATH = Path(
    os.environ.get("LFSRC_SCOPE_PATH", PROJECT_ROOT / "deploy" / "config" / "scope.yaml")
)
RUNS_ROOT = Path(os.environ.get("LFSRC_RUNS_ROOT", PROJECT_ROOT / "runs"))
DATABASE = Path(os.environ.get("LFSRC_DATABASE", RUNS_ROOT / "state.sqlite3"))


def _tokens() -> dict[str, str]:
    raw = os.environ.get("LFSRC_API_TOKENS_JSON", "{}")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError("LFSRC_API_TOKENS_JSON must contain a JSON object")
    return {str(token): str(role) for token, role in value.items()}


app = create_app(
    scope=load_scope(SCOPE_PATH),
    database=DATABASE,
    runs_root=RUNS_ROOT,
    report_root=RUNS_ROOT / "reports",
    evidence_root=RUNS_ROOT / "evidence",
    tokens=_tokens(),
)

web_directory = PROJECT_ROOT / "web" / "dist"
if web_directory.is_dir():
    app.mount("/", StaticFiles(directory=web_directory, html=True), name="console")
