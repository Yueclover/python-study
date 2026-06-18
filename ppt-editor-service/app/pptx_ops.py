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


def _clear_tr_text(tr):
    """清空行内所有单元格的文本内容，保留结构。"""
    for tc in tr.tc_lst:
        # tc.txBody.p_lst 取段落列表（brief 中 tc.iter_paragraphs() 在此版本不存在）
        for p in tc.txBody.p_lst:
            for r in list(p.r_lst):
                r.getparent().remove(r)


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
                tr.append(new_tc)
    elif cols < cur_cols:
        for _ in range(cur_cols - cols):
            grid.remove(grid.gridCol_lst[-1])
            for tr in tbl.tr_lst:
                tr.remove(tr.tc_lst[-1])
