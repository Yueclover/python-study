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
    assert any(b["type"] == "overlap" and b["page"] == 5 for b in bad)


def test_adjacent_leaves_not_flagged():
    pages = [{
        "page": 6, "overflow_right": 0.0, "overflow_bottom": 0.0,
        "leaves": [
            {"x": 0, "y": 0, "w": 100, "h": 50, "text": "上"},
            {"x": 0, "y": 50, "w": 100, "h": 50, "text": "下"},  # 仅相邻不相交
        ],
    }]
    assert analyze_pages(pages) == []
