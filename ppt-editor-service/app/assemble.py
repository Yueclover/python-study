def assemble_plan(page_outputs, skeleton, kept_ids=None):
    """逐页填充结果 -> plan（fill/repeat/drop），保持模板页面顺序。

    kept_ids: 大纲引用过的 slide_id 集合（无论是否有文字槽）。
              - 有 fill 输出的页 → fill / repeat+fill（同原有行为）
              - 在 kept_ids 中但无有效 fill 输出的页 → 原样保留（既不 fill 也不 drop）
              - 不在 kept_ids 中且无 fill 输出的页 → drop（原有行为）
              kept_ids=None 等价于空集合，完全向后兼容。
    """
    kept = set(kept_ids or [])

    # 只统计 fields 非空的输出（空 fields 视为 no-op）
    by_slide = {}
    for o in page_outputs or []:
        sid = o.get("slide_id")
        fields = o.get("fields") or {}
        if not fields:
            continue
        by_slide.setdefault(sid, []).append(fields)

    plan = []
    for sl in skeleton.get("slides", []):
        sid = sl.get("slide_id")
        occs = by_slide.get(sid, [])
        if not occs:
            if sid in kept:
                # 大纲引用但无可填字段 → 原样保留，不发出任何 op
                pass
            else:
                plan.append({"kind": "drop", "slide_id": sid})
        elif len(occs) == 1:
            plan.append({"kind": "fill", "slide_id": sid, "fields": occs[0]})
        else:
            # N>1 occurrences: reuse the ORIGINAL slide for occs[0] and only
            # duplicate the remaining N-1 copies (occs[1:]).  The repeat item
            # must come BEFORE the fill so dup_slide clones the clean template,
            # not the already-filled original.  This prevents a stale unfilled
            # template page from surviving in the output deck.
            plan.append({"kind": "repeat", "slide_id": sid, "items": occs[1:]})
            plan.append({"kind": "fill", "slide_id": sid, "fields": occs[0]})
    return plan
