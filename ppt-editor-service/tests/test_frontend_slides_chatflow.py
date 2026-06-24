from pathlib import Path

DIFY = Path(__file__).resolve().parent.parent / "dify"
CSS = DIFY / "assets" / "frontend-slides" / "viewport-base.css"


def test_vendored_css_present_and_intact():
    assert CSS.is_file(), f"缺少 vendored CSS: {CSS}"
    text = CSS.read_text(encoding="utf-8")
    for marker in [".deck-stage", "width: 1920px", ".slide.active", "prefers-reduced-motion"]:
        assert marker in text, f"viewport-base.css 缺少不变量: {marker}"
