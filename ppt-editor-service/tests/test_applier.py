from pptx import Presentation
from app.applier import apply_ops
from app.parser import parse_presentation


def test_set_text_applied(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    applied, rejected = apply_ops(prs, [
        {"op": "set_text", "shape_id": "s1_sh1", "text": "新标题"},
    ])
    assert applied == 1 and rejected == []
    assert prs.slides[0].shapes[0].text_frame.text == "新标题"


def test_dup_then_fill_copies(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    applied, rejected = apply_ops(prs, [
        {"op": "dup_slide", "slide_id": "s2", "count": 2, "as": ["d1", "d2"]},
        {"op": "set_text", "shape_id": "d1::sh1", "text": "要点一"},
        {"op": "set_text", "shape_id": "d2::sh1", "text": "要点二"},
    ])
    assert applied == 3 and rejected == []
    assert len(prs.slides) == 4
    assert prs.slides[2].shapes[0].text_frame.text == "要点一"
    assert prs.slides[3].shapes[0].text_frame.text == "要点二"


def test_bad_id_rejected_but_others_apply(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    applied, rejected = apply_ops(prs, [
        {"op": "set_text", "shape_id": "s9_sh9", "text": "x"},
        {"op": "set_text", "shape_id": "s1_sh1", "text": "ok"},
    ])
    assert applied == 1
    assert len(rejected) == 1
    assert rejected[0]["index"] == 0
    assert "不存在" in rejected[0]["reason"]
    assert prs.slides[0].shapes[0].text_frame.text == "ok"


def test_del_slide(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    applied, rejected = apply_ops(prs, [{"op": "del_slide", "slide_id": "s1"}])
    assert applied == 1 and rejected == []
    assert len(prs.slides) == 1
