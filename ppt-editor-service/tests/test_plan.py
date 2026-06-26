from app.plan import expand_plan


def test_fill():
    ops, warn = expand_plan(
        [{"kind": "fill", "slide_id": "s1", "fields": {"s1_sh1": "标题", "s1_sh2": "副"}}], {})
    assert warn == []
    assert {"op": "set_text", "shape_id": "s1_sh1", "text": "标题"} in ops
    assert {"op": "set_text", "shape_id": "s1_sh2", "text": "副"} in ops


def test_repeat_generates_dup_and_temp_ids():
    plan = [{"kind": "repeat", "slide_id": "s2", "items": [
        {"s2_sh1": "A1", "s2_sh2": "A2"},
        {"s2_sh1": "B1", "s2_sh2": "B2"},
    ]}]
    ops, warn = expand_plan(plan, {})
    assert ops[0] == {"op": "dup_slide", "slide_id": "s2", "count": 2, "as": ["s2__r1", "s2__r2"]}
    # dup 在所有填充之前
    assert ops[0]["op"] == "dup_slide"
    assert {"op": "set_text", "shape_id": "s2__r1::sh1", "text": "A1"} in ops
    assert {"op": "set_text", "shape_id": "s2__r2::sh2", "text": "B2"} in ops


def test_repeat_empty_items_skipped():
    ops, warn = expand_plan([{"kind": "repeat", "slide_id": "s2", "items": []}], {})
    assert ops == [] and warn == []


def test_repeat_malformed_shape_id_falls_back():
    ops, _ = expand_plan([{"kind": "repeat", "slide_id": "s2",
                           "items": [{"weird": "X"}]}], {})
    assert {"op": "set_text", "shape_id": "s2__r1::weird", "text": "X"} in ops


def test_table_resizes_when_dims_differ():
    structure = {"slides": [{"shapes": [
        {"shape_id": "s3_sh4", "type": "table", "table": {"rows": 3, "cols": 4}}]}]}
    plan = [{"kind": "table", "shape_id": "s3_sh4",
             "rows": [["指标", "前", "后"], ["响应", "30s", "3s"]]}]
    ops, _ = expand_plan(plan, structure)
    assert ops[0] == {"op": "set_table_size", "shape_id": "s3_sh4", "rows": 2, "cols": 3}
    assert {"op": "set_cell", "shape_id": "s3_sh4", "r": 0, "c": 0, "text": "指标"} in ops
    assert {"op": "set_cell", "shape_id": "s3_sh4", "r": 1, "c": 2, "text": "3s"} in ops


def test_table_no_resize_when_dims_match():
    structure = {"slides": [{"shapes": [
        {"shape_id": "s3_sh4", "type": "table", "table": {"rows": 1, "cols": 2}}]}]}
    ops, _ = expand_plan([{"kind": "table", "shape_id": "s3_sh4",
                           "rows": [["a", "b"]]}], structure)
    assert all(o["op"] != "set_table_size" for o in ops)


def test_drop():
    ops, _ = expand_plan([{"kind": "drop", "slide_id": "s4"}], {})
    assert ops == [{"op": "del_slide", "slide_id": "s4"}]


def test_unknown_kind_warns():
    ops, warn = expand_plan([{"kind": "frobnicate"}], {})
    assert ops == []
    assert any("frobnicate" in w for w in warn)


def test_repeat_cross_page_field_skipped_with_warning():
    plan = [{"kind": "repeat", "slide_id": "s2",
             "items": [{"s2_sh1": "ok", "s5_sh1": "wrong"}]}]
    ops, warn = expand_plan(plan, {})
    # same-page field must be emitted
    assert {"op": "set_text", "shape_id": "s2__r1::sh1", "text": "ok"} in ops
    # cross-page field must NOT appear in any op
    assert not any("s5" in str(o) for o in ops)
    assert not any(o.get("text") == "wrong" for o in ops)
    # warning must mention the cross-page field
    assert any("s5_sh1" in w for w in warn)
