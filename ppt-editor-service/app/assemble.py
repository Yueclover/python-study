def assemble_plan(page_outputs, skeleton):
    """逐页填充结果 -> plan（fill/repeat/drop），保持模板页面顺序。"""
    by_slide = {}
    for o in page_outputs or []:
        sid = o.get("slide_id")
        by_slide.setdefault(sid, []).append(o.get("fields") or {})
    plan = []
    for sl in skeleton.get("slides", []):
        sid = sl.get("slide_id")
        occs = by_slide.get(sid, [])
        if not occs:
            plan.append({"kind": "drop", "slide_id": sid})
        elif len(occs) == 1:
            plan.append({"kind": "fill", "slide_id": sid, "fields": occs[0]})
        else:
            plan.append({"kind": "repeat", "slide_id": sid, "items": occs})
    return plan
