from app.assemble import assemble_plan


def test_single_use_becomes_fill():
    sk = {"slides": [{"slide_id": "s1"}]}
    out = [{"slide_id": "s1", "fields": {"s1_sh1": "A"}}]
    assert assemble_plan(out, sk) == [
        {"kind": "fill", "slide_id": "s1", "fields": {"s1_sh1": "A"}}]


def test_multiple_use_becomes_repeat_in_order():
    sk = {"slides": [{"slide_id": "s5"}]}
    out = [{"slide_id": "s5", "fields": {"s5_sh1": "A"}},
           {"slide_id": "s5", "fields": {"s5_sh1": "B"}}]
    assert assemble_plan(out, sk) == [
        {"kind": "repeat", "slide_id": "s5",
         "items": [{"s5_sh1": "A"}, {"s5_sh1": "B"}]}]


def test_unreferenced_slide_dropped():
    sk = {"slides": [{"slide_id": "s1"}, {"slide_id": "s2"}]}
    out = [{"slide_id": "s1", "fields": {"s1_sh1": "A"}}]
    plan = assemble_plan(out, sk)
    assert {"kind": "fill", "slide_id": "s1", "fields": {"s1_sh1": "A"}} in plan
    assert {"kind": "drop", "slide_id": "s2"} in plan


def test_output_follows_template_order():
    sk = {"slides": [{"slide_id": "s1"}, {"slide_id": "s2"}, {"slide_id": "s3"}]}
    out = [{"slide_id": "s3", "fields": {"x": "3"}},
           {"slide_id": "s1", "fields": {"x": "1"}}]
    plan = assemble_plan(out, sk)
    assert [p["slide_id"] for p in plan] == ["s1", "s2", "s3"]
    assert plan[1] == {"kind": "drop", "slide_id": "s2"}


def test_unknown_slide_id_ignored():
    sk = {"slides": [{"slide_id": "s1"}]}
    out = [{"slide_id": "s1", "fields": {"x": "1"}},
           {"slide_id": "zzz", "fields": {"y": "2"}}]
    plan = assemble_plan(out, sk)
    assert plan == [{"kind": "fill", "slide_id": "s1", "fields": {"x": "1"}}]
