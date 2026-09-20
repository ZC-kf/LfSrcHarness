"""The supplied starfield image is packaged unchanged as the desktop background."""

import hashlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parents[1]


def test_supplied_starfield_is_in_web_bundle_sources() -> None:
    image_path = ROOT / "web" / "public" / "starfield.png"
    assert image_path.is_file()
    assert hashlib.sha256(image_path.read_bytes()).hexdigest() == (
        "6b23d3cb29f0add1739e632b215c6811b8697ef47b437a59a4f751b0cc430a6e"
    )
    with Image.open(image_path) as image:
        assert image.size == (1672, 941)


def test_desktop_theme_references_supplied_background_and_icon() -> None:
    stylesheet = (ROOT / "web" / "src" / "styles.css").read_text(encoding="utf-8")
    app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert 'url("/starfield.png")' in stylesheet
    assert 'src="/lfsrc-icon.png"' in app
    assert (ROOT / "web" / "public" / "lfsrc-icon.png").is_file()
