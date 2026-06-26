from pptx import Presentation
from app.parser import parse_presentation


def test_parse_basic_structure(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    doc = parse_presentation(prs)
    assert doc["slide_size"]["width"] > 0
    assert len(doc["slides"]) == 2

    s1 = doc["slides"][0]
    assert s1["slide_id"] == "s1"
    assert s1["index"] == 0
    assert isinstance(s1["layout_name"], str)

    title = s1["shapes"][0]
    assert title["shape_id"] == "s1_sh1"
    assert title["type"] == "text"
    assert title["ph_type"] == "title"
    assert title["text"] == "原标题"
    assert title["style"]["size"] is None or isinstance(title["style"]["size"], int)
    for k in ("x", "y", "w", "h"):
        assert k in title["pos"]


def test_parse_table(table_pptx_path):
    prs = Presentation(table_pptx_path)
    doc = parse_presentation(prs)
    tbl_shapes = [s for s in doc["slides"][0]["shapes"] if s["type"] == "table"]
    assert len(tbl_shapes) == 1
    t = tbl_shapes[0]["table"]
    assert t["rows"] == 3 and t["cols"] == 4
    assert {"r": 0, "c": 0, "text": "季度"} in t["cells"]
