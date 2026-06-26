import re


def _slot_role(shape):
    ph = shape.get("ph_type")
    t = shape.get("type")
    if ph == "title":
        return "title"
    if ph == "subtitle":
        return "subtitle"
    if ph == "body":
        return "body"
    if t == "table":
        return "table"
    if t in ("picture", "chart"):
        return "media"
    return "other"


_COVER_KW = ("封面", "标题幻灯片", "title slide", "cover")
_TOC_KW = ("目录", "contents", "agenda", "outline", "大纲")
_SECTION_KW = ("节标题", "过渡", "section", "divider", "part")
_ENDING_KW = ("结束", "谢谢", "感谢", "致谢", "封底", "thank", "the end")
_SECTION_RE = re.compile(
    r"(第\s*[一二三四五六七八九十\d]+\s*[章节篇部])|(\bpart\s*\d)|(\bchapter\s*\d)",
    re.I)


def _has(text, kws):
    t = (text or "").lower()
    return any(k.lower() in t for k in kws)


def _page_role(slot_roles, layout_name="", page_text="", index=0, total=0):
    if "table" in slot_roles:
        return "table"
    # 2. layout_name（最强信号）
    if _has(layout_name, _COVER_KW):
        return "cover"
    if _has(layout_name, _TOC_KW):
        return "toc"
    if _has(layout_name, _SECTION_KW):
        return "section"
    if _has(layout_name, _ENDING_KW):
        return "ending"
    # 3. 页面正文关键词
    if _has(page_text, _TOC_KW):
        return "toc"
    if _has(page_text, _ENDING_KW):
        return "ending"
    if _SECTION_RE.search(page_text or ""):
        return "section"
    # 4. 页序
    if index == 0 and "title" in slot_roles:
        return "cover"
    if total and index == total - 1:
        text_slots = [r for r in slot_roles
                      if r in ("title", "subtitle", "body", "other")]
        if len(text_slots) <= 1 and "body" not in slot_roles:
            return "ending"
    # 5. 槽位组合兜底
    if "title" in slot_roles and "subtitle" in slot_roles:
        return "cover"
    if "title" in slot_roles and "body" in slot_roles:
        return "content"
    # 6.
    return "generic"


def _slot(shape):
    s = {
        "shape_id": shape["shape_id"],
        "role": _slot_role(shape),
        "type": shape["type"],
        "current_text": shape.get("text") or "",
        "editable": shape["type"] == "text",
    }
    if shape["type"] == "table" and "table" in shape:
        s["rows"] = shape["table"]["rows"]
        s["cols"] = shape["table"]["cols"]
    return s


def build_skeleton(parsed):
    slides = []
    total = len(parsed["slides"])
    for sl in parsed["slides"]:
        slots = [_slot(sh) for sh in sl["shapes"]]
        page_text = " ".join(
            sh.get("text") or "" for sh in sl["shapes"]).strip()
        role = _page_role([s["role"] for s in slots],
                          sl["layout_name"], page_text,
                          sl["index"], total)
        slides.append({
            "slide_id": sl["slide_id"],
            "role": role,
            "layout_name": sl["layout_name"],
            "slots": slots,
        })
    return {"slides": slides}
