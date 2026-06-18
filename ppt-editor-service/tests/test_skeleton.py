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
