from pptx import Presentation
from app.parser import parse_presentation
from app.applier import apply_ops


def test_full_mechanical_roundtrip(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    doc = parse_presentation(prs)
    assert len(doc["slides"]) == 2

    # 手写一份「改标题 + 复制要点页3份分别填内容 + 删原首页」的指令
    ops = [
        {"op": "dup_slide", "slide_id": "s2", "count": 3, "as": ["d1", "d2", "d3"]},
        {"op": "set_text", "shape_id": "d1::sh1", "text": "要点一"},
        {"op": "set_text", "shape_id": "d2::sh1", "text": "要点二"},
        {"op": "set_text", "shape_id": "d3::sh1", "text": "要点三"},
        {"op": "del_slide", "slide_id": "s1"},
    ]
    applied, rejected = apply_ops(prs, ops)
    assert rejected == []
    assert applied == 5

    # 重新解析验证最终结构
    doc2 = parse_presentation(prs)
    titles = [s["shapes"][0]["text"] for s in doc2["slides"]]
    # 原首页已删，剩：原要点页 + 3 张副本
    assert "要点一" in titles and "要点二" in titles and "要点三" in titles
    assert len(doc2["slides"]) == 4
