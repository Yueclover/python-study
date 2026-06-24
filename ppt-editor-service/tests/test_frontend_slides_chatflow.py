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


import yaml

BUILD = DIFY / "build_frontend_slides_chatflow.py"
YML = DIFY / "frontend-slides-chatflow.yml"


def _load_build():
    spec = importlib.util.spec_from_file_location("fs_build", BUILD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _nodes(app):
    return {n["id"]: n for n in app["workflow"]["graph"]["nodes"]}


def _edges(app):
    return {(e["source"], e["target"]) for e in app["workflow"]["graph"]["edges"]}


def test_app_is_advanced_chat_with_four_linear_nodes():
    app = _load_build().build_app()
    assert app["app"]["mode"] == "advanced-chat"
    assert app["kind"] == "app"
    nodes = _nodes(app)
    assert set(nodes) == {"start", "plan", "render", "answer"}
    assert nodes["start"]["data"]["type"] == "start"
    assert nodes["plan"]["data"]["type"] == "llm"
    assert nodes["render"]["data"]["type"] == "llm"
    assert nodes["answer"]["data"]["type"] == "answer"
    assert _edges(app) == {("start", "plan"), ("plan", "render"), ("render", "answer")}


def test_nodes_wire_prompts_and_streaming_answer():
    mod = _load_build()
    app = mod.build_app()
    nodes = _nodes(app)
    # plan 节点挂 plan 提示词,user 引用 sys.query
    plan_sys = nodes["plan"]["data"]["prompt_template"][0]["text"]
    assert "Bold Signal" in plan_sys and '"outline"' in plan_sys
    plan_user = nodes["plan"]["data"]["prompt_template"][1]["text"]
    assert "{{#sys.query#}}" in plan_user
    # render 节点挂 render 提示词(含内联 CSS),user 引用 plan.text
    render_sys = nodes["render"]["data"]["prompt_template"][0]["text"]
    assert ".deck-stage" in render_sys and "SlidePresentation" in render_sys
    render_user = nodes["render"]["data"]["prompt_template"][1]["text"]
    assert "{{#plan.text#}}" in render_user
    # answer 用 ```html 包裹 render 输出(保留流式)
    ans = nodes["answer"]["data"]["answer"]
    assert "```html" in ans and "{{#render.text#}}" in ans


def test_build_writes_loadable_yaml(tmp_path):
    mod = _load_build()
    app = mod.build_app()
    out = tmp_path / "out.yml"
    out.write_text(yaml.safe_dump(app, allow_unicode=True, sort_keys=False), encoding="utf-8")
    reloaded = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert reloaded["app"]["mode"] == "advanced-chat"
