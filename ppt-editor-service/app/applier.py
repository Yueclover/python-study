from .ids import IdIndex
from . import pptx_ops


class OpError(Exception):
    pass


def _set_text(idx, op):
    shp = idx.shape(op["shape_id"])
    if shp is None:
        raise OpError(f'shape_id {op["shape_id"]} 不存在')
    if not shp.has_text_frame:
        raise OpError(f'shape_id {op["shape_id"]} 不是文本框')
    pptx_ops.set_text_keep_style(shp.text_frame, op["text"])


def _set_cell(idx, op):
    shp = idx.shape(op["shape_id"])
    if shp is None or not shp.has_table:
        raise OpError(f'shape_id {op["shape_id"]} 不是表格')
    try:
        pptx_ops.set_cell(shp, op["r"], op["c"], op["text"])
    except IndexError:
        raise OpError(f'单元格 ({op["r"]},{op["c"]}) 越界')


def _set_table_size(idx, op):
    shp = idx.shape(op["shape_id"])
    if shp is None or not shp.has_table:
        raise OpError(f'shape_id {op["shape_id"]} 不是表格')
    pptx_ops.set_table_size(shp, op["rows"], op["cols"])


def _dup_slide(prs, idx, op):
    src = idx.slide(op["slide_id"])
    if src is None:
        raise OpError(f'slide_id {op["slide_id"]} 不存在')
    names = op.get("as") or []
    count = op.get("count", len(names))
    if len(names) != count:
        raise OpError("count 与 as 数量不一致")
    new_slides = pptx_ops.duplicate_slide_after(prs, src, count)
    for name, ns in zip(names, new_slides):
        idx.register_temp_slide(name, ns)


def _del_slide(prs, idx, op):
    s = idx.slide(op["slide_id"])
    if s is None:
        raise OpError(f'slide_id {op["slide_id"]} 不存在')
    pptx_ops.delete_slide(prs, s)


def _dispatch(prs, idx, op):
    kind = op.get("op")
    if kind == "set_text":
        _set_text(idx, op)
    elif kind == "set_cell":
        _set_cell(idx, op)
    elif kind == "set_table_size":
        _set_table_size(idx, op)
    elif kind == "dup_slide":
        _dup_slide(prs, idx, op)
    elif kind == "del_slide":
        _del_slide(prs, idx, op)
    else:
        raise OpError(f"未知指令 {kind}")


def apply_ops(prs, ops):
    idx = IdIndex(prs)
    rejected = []
    applied = 0
    for i, op in enumerate(ops):
        try:
            _dispatch(prs, idx, op)
            applied += 1
        except (OpError, KeyError) as e:
            reason = str(e) if isinstance(e, OpError) else f"缺少参数 {e}"
            rejected.append({"index": i, "op": op.get("op"), "reason": reason})
    return applied, rejected
