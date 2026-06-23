from app.validate import analyze_pages


def test_clean_page_has_no_issue():
    pages = [{
        "page": 1, "overflow_right": 0.0, "overflow_bottom": 0.0,
        "leaves": [
            {"x": 0, "y": 0, "w": 100, "h": 20, "text": "A"},
            {"x": 0, "y": 40, "w": 100, "h": 20, "text": "B"},
        ],
    }]
    assert analyze_pages(pages) == []


def test_bottom_overflow_flagged():
    pages = [{"page": 3, "overflow_right": 0.0, "overflow_bottom": 80.0, "leaves": []}]
    bad = analyze_pages(pages)
    assert len(bad) == 1
    assert bad[0]["page"] == 3
    assert bad[0]["type"] == "overflow"
    assert "下" in bad[0]["detail"] and "80" in bad[0]["detail"]


def test_small_overflow_within_tolerance_ignored():
    pages = [{"page": 2, "overflow_right": 1.5, "overflow_bottom": 0.0, "leaves": []}]
    assert analyze_pages(pages) == []


def test_overlapping_leaves_flagged():
    pages = [{
        "page": 5, "overflow_right": 0.0, "overflow_bottom": 0.0,
        "leaves": [
            {"x": 0, "y": 0, "w": 100, "h": 100, "text": "标题"},
            {"x": 0, "y": 50, "w": 100, "h": 100, "text": "正文"},  # 50% 纵向重叠
        ],
    }]
    bad = analyze_pages(pages)
    overlaps = [b for b in bad if b["type"] == "overlap" and b["page"] == 5]
    assert overlaps, "应检出第5页文本重叠"
    detail = overlaps[0]["detail"]
    assert "%" in detail
    assert "标题" in detail or "正文" in detail


def test_adjacent_leaves_not_flagged():
    pages = [{
        "page": 6, "overflow_right": 0.0, "overflow_bottom": 0.0,
        "leaves": [
            {"x": 0, "y": 0, "w": 100, "h": 50, "text": "上"},
            {"x": 0, "y": 50, "w": 100, "h": 50, "text": "下"},  # 仅相邻不相交
        ],
    }]
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


def test_validate_endpoint_failopen_on_garbage():
    # 不依赖浏览器：空 html 渲染后无 section，应返回空坏页
    resp = client.post("/validate", json={"html": ""})
    assert resp.status_code == 200
    assert "bad_pages" in resp.json()
