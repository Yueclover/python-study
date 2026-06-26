from app.validate import analyze_pages, check_section_overflow, validate_html


def test_clean_page_has_no_issue():
    pages = [{"page": 1, "overflow_right": 0.0, "overflow_bottom": 0.0}]
    assert analyze_pages(pages) == []


def test_bottom_overflow_flagged():
    pages = [{"page": 3, "overflow_right": 0.0, "overflow_bottom": 80.0}]
    bad = analyze_pages(pages)
    assert len(bad) == 1
    assert bad[0]["page"] == 3
    assert bad[0]["type"] == "overflow"
    assert "下" in bad[0]["detail"] and "80" in bad[0]["detail"]


def test_right_overflow_flagged():
    pages = [{"page": 4, "overflow_right": 50.0, "overflow_bottom": 0.0}]
    bad = analyze_pages(pages)
    assert len(bad) == 1
    assert bad[0]["type"] == "overflow"
    assert "右" in bad[0]["detail"] and "50" in bad[0]["detail"]


def test_small_overflow_within_tolerance_ignored():
    pages = [{"page": 2, "overflow_right": 1.5, "overflow_bottom": 0.0}]
    assert analyze_pages(pages) == []


# ---------------------------------------------------------------------------
# Task 2: 集成测试（无 Chromium 自动跳过）
# ---------------------------------------------------------------------------
import importlib.util
import pytest
from fastapi.testclient import TestClient
from app.main import app

_HAS_PW = importlib.util.find_spec("playwright") is not None
client = TestClient(app)


def _chromium_ok() -> bool:
    if not _HAS_PW:
        return False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark_browser = pytest.mark.skipif(
    not _chromium_ok(), reason="Playwright/Chromium 不可用")

_OVERFLOW_HTML = """
<section id="slide-1" class="slide" style="width:960px;height:540px;overflow:hidden;position:relative;">
  <div style="position:absolute;top:900px;">超出页面底部的内容</div>
</section>
"""

_CLEAN_HTML = """
<section id="slide-1" class="slide" style="width:960px;height:540px;overflow:hidden;position:relative;">
  <div style="position:absolute;top:20px;">正常内容</div>
</section>
"""


@pytestmark_browser
def test_validate_detects_overflow():
    resp = client.post("/validate", json={"html": _OVERFLOW_HTML})
    assert resp.status_code == 200
    pages = resp.json()["bad_pages"]
    assert any(p["page"] == 1 and p["type"] == "overflow" for p in pages)


@pytestmark_browser
def test_validate_clean_page():
    resp = client.post("/validate", json={"html": _CLEAN_HTML})
    assert resp.status_code == 200
    assert resp.json()["bad_pages"] == []


@pytestmark_browser
def test_check_section_overflow_on_fragment():
    result = check_section_overflow(_OVERFLOW_HTML)
    assert result["found"] is True
    assert result["overflow"] is True
    assert result["overflow_bottom"] > 300


def test_validate_endpoint_failopen_on_garbage():
    # 不依赖浏览器：空 html 渲染后无 section，应返回空坏页
    resp = client.post("/validate", json={"html": ""})
    assert resp.status_code == 200
    assert "bad_pages" in resp.json()


# ---------------------------------------------------------------------------
# 伪元素不参与溢出检测：仅 ::before/::after 伸出页面不应判为溢出
# ---------------------------------------------------------------------------
_PSEUDO_OVERFLOW_HTML = """
<section id="slide-1" class="slide" style="width:960px;height:540px;overflow:hidden;position:relative;box-sizing:border-box;">
  <style scoped>
    .slide::after{content:'';position:absolute;top:700px;left:0;width:10px;height:200px;background:red;}
  </style>
  <div style="position:absolute;top:20px;">正常内容</div>
</section>
"""


@pytestmark_browser
def test_pseudo_element_overflow_not_flagged():
    resp = client.post("/validate", json={"html": _PSEUDO_OVERFLOW_HTML})
    assert resp.status_code == 200
    assert resp.json()["bad_pages"] == []


# ---------------------------------------------------------------------------
# /fix 接口：等比缩放修复 section 内容溢出（保持宽高不变，忽略装饰性伪元素）
# ---------------------------------------------------------------------------
_FIX_OVERFLOW_HTML = """
<section id="slide-1" class="slide">
  <style scoped>
    .slide { width:960px; height:540px; box-sizing:border-box; padding:40px;
             display:flex; flex-direction:column; overflow:hidden;
             background:#111; color:#fff; }
    .t { font-size:36px; margin:0 0 20px; }
    .body { flex:1; }
  </style>
  <h2 class="t">标题</h2>
  <div class="body"><div style="height:800px;">很高的内容块</div></div>
</section>
"""


@pytestmark_browser
def test_fix_endpoint_scales_overflowing_content():
    resp = client.post("/fix", json={"html": _FIX_OVERFLOW_HTML})
    assert resp.status_code == 200
    fixed = resp.json()["html"]
    assert "scale(" in fixed
    assert validate_html(fixed)["bad_pages"] == []


@pytestmark_browser
def test_fix_endpoint_ignores_decorative_pseudo():
    resp = client.post("/fix", json={"html": _PSEUDO_OVERFLOW_HTML})
    assert resp.status_code == 200
    fixed = resp.json()["html"]
    assert "scale(" not in fixed
