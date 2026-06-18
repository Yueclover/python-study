import copy


def set_text_keep_style(text_frame, new_text):
    """替换文本但保留首段首个 run 的字体样式。"""
    para = text_frame.paragraphs[0]
    if para.runs:
        run = para.runs[0]
        run.text = new_text
        for extra in para.runs[1:]:
            extra._r.getparent().remove(extra._r)
    else:
        run = para.add_run()
        run.text = new_text
    for extra_para in text_frame.paragraphs[1:]:
        extra_para._p.getparent().remove(extra_para._p)


def set_cell(table_shape, r, c, text):
    table = table_shape.table
    cell = table.cell(r, c)  # 越界抛 IndexError，由 applier 捕获
    set_text_keep_style(cell.text_frame, text)


def _clear_tc_text(tc):
    """清空单个单元格的文本内容，保留结构。"""
    for p in tc.txBody.p_lst:
        for r in list(p.r_lst):
            r.getparent().remove(r)


def _clear_tr_text(tr):
    """清空行内所有单元格的文本内容，保留结构。"""
    for tc in tr.tc_lst:
        _clear_tc_text(tc)


def set_table_size(table_shape, rows, cols):
    tbl = table_shape.table._tbl
    # 行
    cur_rows = len(tbl.tr_lst)
    if rows > cur_rows:
        for _ in range(rows - cur_rows):
            new_tr = copy.deepcopy(tbl.tr_lst[-1])
            _clear_tr_text(new_tr)
            tbl.append(new_tr)
    elif rows < cur_rows:
        for tr in list(tbl.tr_lst[rows:]):
            tbl.remove(tr)
    # 列
    grid = tbl.tblGrid
    cur_cols = len(grid.gridCol_lst)
    if cols > cur_cols:
        for _ in range(cols - cur_cols):
            grid.append(copy.deepcopy(grid.gridCol_lst[-1]))
            for tr in tbl.tr_lst:
                new_tc = copy.deepcopy(tr.tc_lst[-1])
                _clear_tc_text(new_tc)
                tr.append(new_tc)
    elif cols < cur_cols:
        for _ in range(cur_cols - cols):
            grid.remove(grid.gridCol_lst[-1])
            for tr in tbl.tr_lst:
                tr.remove(tr.tc_lst[-1])


def slide_index(prs, slide):
    target = slide.slide_id
    for i, s in enumerate(prs.slides):
        if s.slide_id == target:
            return i
    return -1


def _move_slide(prs, from_index, to_index):
    sldIdLst = prs.slides._sldIdLst
    ids = list(sldIdLst)
    el = ids[from_index]
    sldIdLst.remove(el)
    sldIdLst.insert(to_index, el)


def _copy_slide(prs, source_slide):
    new_slide = prs.slides.add_slide(source_slide.slide_layout)
    # 移除 add_slide 自动生成的占位符
    for shp in list(new_slide.shapes):
        shp._element.getparent().remove(shp._element)
    # 复制源页所有形状
    for shp in source_slide.shapes:
        new_slide.shapes._spTree.append(copy.deepcopy(shp._element))
    return new_slide


def duplicate_slide_after(prs, source_slide, count):
    base_index = slide_index(prs, source_slide)
    new_slides = []
    for k in range(count):
        ns = _copy_slide(prs, source_slide)  # 追加在末尾
        from_idx = slide_index(prs, ns)
        _move_slide(prs, from_idx, base_index + 1 + k)
        new_slides.append(ns)
    return new_slides


def delete_slide(prs, slide):
    idx = slide_index(prs, slide)
    if idx < 0:
        return False
    sldIdLst = prs.slides._sldIdLst
    sldIdLst.remove(list(sldIdLst)[idx])
    return True
