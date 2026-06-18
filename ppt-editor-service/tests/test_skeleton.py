from pptx import Presentation
from app.parser import parse_presentation
from app.skeleton import build_skeleton


def test_skeleton_cover_and_content(basic_pptx_path):
    parsed = parse_presentation(Presentation(basic_pptx_path))
    sk = build_skeleton(parsed)
    assert len(sk["slides"]) == 2
    s1 = sk["slides"][0]
    assert s1["slide_id"] == "s1"
    assert s1["role"] == "cover"            # title + subtitle
    roles = {slot["role"] for slot in s1["slots"]}
    assert "title" in roles and "subtitle" in roles
    # 标题槽 shape_id 与解析一致
    title_slot = next(s for s in s1["slots"] if s["role"] == "title")
    assert title_slot["shape_id"] == "s1_sh1"
    assert sk["slides"][1]["role"] == "content"   # title + body


def test_skeleton_table_page(table_pptx_path):
    parsed = parse_presentation(Presentation(table_pptx_path))
    sk = build_skeleton(parsed)
    page = sk["slides"][0]
    assert page["role"] == "table"
    tslot = next(s for s in page["slots"] if s["role"] == "table")
    assert tslot["type"] == "table"
    assert tslot["rows"] == 3 and tslot["cols"] == 4


def test_slot_has_full_current_text_and_editable(basic_pptx_path):
    parsed = parse_presentation(Presentation(basic_pptx_path))
    sk = build_skeleton(parsed)
    title_slot = next(s for s in sk["slides"][0]["slots"] if s["role"] == "title")
    assert title_slot["current_text"] == "原标题"     # 全文，不截断
    assert title_slot["editable"] is True
    assert "sample" not in title_slot


def test_table_slot_not_editable(table_pptx_path):
    parsed = parse_presentation(Presentation(table_pptx_path))
    sk = build_skeleton(parsed)
    tslot = next(s for s in sk["slides"][0]["slots"] if s["role"] == "table")
    assert tslot["editable"] is False
