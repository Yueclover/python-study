from pathlib import Path
import importlib.util

DIFY = Path(__file__).resolve().parent.parent / "dify"
CSS = DIFY / "assets" / "frontend-slides" / "viewport-base.css"

PROMPTS = DIFY / "frontend_slides_prompts.py"
PRESET_NAMES = [
    "Bold Signal", "Electric Studio", "Creative Voltage", "Dark Botanical",
    "Notebook Tabs", "Pastel Geometry", "Split Pastel", "Vintage Editorial",
    "Neon Cyber", "Terminal Green", "Swiss Modern", "Paper & Ink",
]


def test_vendored_css_present_and_intact():
    assert CSS.is_file(), f"缺少 vendored CSS: {CSS}"
    text = CSS.read_text(encoding="utf-8")
    for marker in [".deck-stage", "width: 1920px", ".slide.active", "prefers-reduced-motion"]:
        assert marker in text, f"viewport-base.css 缺少不变量: {marker}"


def _load_prompts():
    spec = importlib.util.spec_from_file_location("fs_prompts", PROMPTS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_plan_prompt_lists_all_presets_and_contract():
    mod = _load_prompts()
    p = mod.PLAN_SYSTEM_PROMPT
    for name in PRESET_NAMES:
        assert name in p, f"plan 提示词缺少预设: {name}"
    for key in ['"style"', '"theme"', '"density"', '"outline"', '"role"']:
        assert key in p, f"plan 提示词缺少 JSON 契约键: {key}"


def test_render_prompt_inlines_css_and_rules():
    mod = _load_prompts()
    r = mod.build_render_system_prompt()
    css = CSS.read_text(encoding="utf-8")
    # 证明 CSS 被原样内联
    for marker in [".deck-stage", ".slide.active", "prefers-reduced-motion"]:
        assert marker in r
    assert "width: 1920px" in r
    # 证明 CSS 文件内容（不只是脚手架文本）被内联
    assert "MANDATORY BASE STYLES" in r, "CSS 文件头注释未被内联"
    assert "transform-origin: 0 0;" in r, "CSS transform-origin 规则未被内联"
    # 脚手架与铁律
    for token in ["SlidePresentation", "setupStageScale", "<!DOCTYPE html>"]:
        assert token in r, f"render 提示词缺少脚手架标记: {token}"
    # fail-open 与"只输出 HTML"
    assert "尽力" in r
    assert "只输出" in r or "只返回" in r
