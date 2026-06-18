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


def _page_role(slot_roles):
    if "table" in slot_roles:
        return "table"
    if "title" in slot_roles and "subtitle" in slot_roles:
        return "cover"
    if "title" in slot_roles and "body" in slot_roles:
        return "content"
    return "generic"


def _slot(shape):
    s = {
        "shape_id": shape["shape_id"],
        "role": _slot_role(shape),
        "type": shape["type"],
    }
    text = shape.get("text")
    if text:
        s["sample"] = text[:30]
    if shape["type"] == "table" and "table" in shape:
        s["rows"] = shape["table"]["rows"]
        s["cols"] = shape["table"]["cols"]
    return s


def build_skeleton(parsed):
    slides = []
    for sl in parsed["slides"]:
        slots = [_slot(sh) for sh in sl["shapes"]]
        slides.append({
            "slide_id": sl["slide_id"],
            "role": _page_role([s["role"] for s in slots]),
            "slots": slots,
        })
    return {"slides": slides}
