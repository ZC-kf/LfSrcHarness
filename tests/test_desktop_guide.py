from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_desktop_guide_is_linked_from_repository_entry_points() -> None:
    guide = ROOT / "docs" / "DESKTOP_GUIDE.md"
    assert guide.is_file()
    for entry in (ROOT / "README.md", ROOT / "docs" / "INSTALL.md", ROOT / "docs" / "README.md"):
        assert "DESKTOP_GUIDE.md" in entry.read_text(encoding="utf-8")


def test_desktop_guide_names_preview_capability_limits() -> None:
    guide = (ROOT / "docs" / "DESKTOP_GUIDE.md").read_text(encoding="utf-8")
    for term in ("模型", "授权范围", "全局急停", "尚未", "不包含"):
        assert term in guide
