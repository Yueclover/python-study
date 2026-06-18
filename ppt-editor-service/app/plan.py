def _short_id(shape_id):
    return shape_id.rsplit("_", 1)[-1] if "_" in shape_id else shape_id


def _table_dims(structure, shape_id):
    for sl in structure.get("slides", []):
        for sh in sl.get("shapes", []):
            if sh.get("shape_id") == shape_id and sh.get("type") == "table":
                t = sh.get("table", {})
                return t.get("rows"), t.get("cols")
    return None, None


def expand_plan(plan, structure):
    ops = []
    warnings = []
    for item in plan or []:
        kind = item.get("kind")
        if kind == "fill":
            for sid, text in (item.get("fields") or {}).items():
                ops.append({"op": "set_text", "shape_id": sid, "text": text})
        elif kind == "repeat":
            items = item.get("items") or []
            if not items:
                continue
            slide_id = item.get("slide_id")
            names = [f"{slide_id}__r{i + 1}" for i in range(len(items))]
            ops.append({"op": "dup_slide", "slide_id": slide_id,
                        "count": len(items), "as": names})
            for name, fields in zip(names, items):
                for sid, text in (fields or {}).items():
                    ops.append({"op": "set_text",
                                "shape_id": f"{name}::{_short_id(sid)}",
                                "text": text})
        elif kind == "table":
            shape_id = item.get("shape_id")
            rows = item.get("rows") or []
            if not rows:
                continue
            nrows = len(rows)
            ncols = len(rows[0])
            cur = _table_dims(structure, shape_id)
            if cur != (nrows, ncols):
                ops.append({"op": "set_table_size", "shape_id": shape_id,
                            "rows": nrows, "cols": ncols})
            for r, row in enumerate(rows):
                for c in range(ncols):
                    val = row[c] if c < len(row) else ""
                    ops.append({"op": "set_cell", "shape_id": shape_id,
                                "r": r, "c": c, "text": val})
        elif kind == "drop":
            ops.append({"op": "del_slide", "slide_id": item.get("slide_id")})
        else:
            warnings.append(f"unknown kind: {kind}")
    return ops, warnings
