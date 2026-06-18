# PPT 模板 LLM 编辑系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 FastAPI 服务，把上传的 PPT 模板解析成带稳定 ID 的 JSON，并按 LLM 产出的编辑指令清单回写成新的 .pptx；再用 Dify 工作流把解析→LLM→回写串成端到端流程。

**Architecture:** 「编辑指令模式」。PPT 服务是纯机械手：`/parse` 把 pptx 按确定性遍历分配 ID 后输出 JSON，`/apply` 重新打开同一份原始 pptx、用同一套确定性遍历重建 ID→对象映射、按指令逐条校验并应用、另存输出。语义识别全部交给 Dify 里的 LLM，服务不懂业务。

**Tech Stack:** Python 3.11+、FastAPI、python-pptx、pytest、FastAPI TestClient（httpx）、Dify 工作流。

## Global Constraints

- 服务目录：`ppt-editor-service/`，应用包 `app/`，测试 `tests/`。
- ID 方案（解析与回写共用、确定性、不落盘序列化对象）：
  - slide_id = `s{index+1}`（如第 1 页 = `s1`）
  - 形状短 ID = `sh{order+1}`（页内按 `slide.shapes` 顺序，如第 3 个 = `sh3`）
  - 完整 shape_id = `{slide_id}_{short}`（如 `s1_sh3`）
  - 副本临时引用 = `{临时页ID}::{短ID}`（如 `d1::sh2`）
- v1 指令集仅 5 条：`set_text` / `set_cell` / `set_table_size` / `dup_slide` / `del_slide`。
- 坐标一律用 EMU 原值（int），不做单位换算。
- 回写从 `source.pptx`（原始模板）出发，结果另存 `{doc_id}-out.pptx`，绝不覆盖原文件。
- 错误处理原则：单条指令非法 → 进 `rejected[]`，不影响其余；能局部拒绝就不整体失败。
- 存储 v1 用本地盘，根目录由环境变量 `PPT_STORAGE` 指定，默认 `./storage`。
- **与 spec 的一处实现细化**：spec 提到 `idmap.json`。因 ID 由确定性遍历产生，`/apply` 重新遍历即可重建完全相同的映射，故无需序列化映射文件；磁盘只保存 `source.pptx` 与输出文件。映射逻辑由 `app/ids.py` 的 `IdIndex` 单一实现，parse/apply 共用，满足 spec「两次调用共享同一 ID 映射」的本意。

---

### Task 1: 项目骨架与健康检查

**Files:**
- Create: `ppt-editor-service/requirements.txt`
- Create: `ppt-editor-service/app/__init__.py`
- Create: `ppt-editor-service/app/main.py`
- Create: `ppt-editor-service/tests/__init__.py`
- Test: `ppt-editor-service/tests/test_health.py`

**Interfaces:**
- Consumes: 无
- Produces: `app.main:app`（FastAPI 实例）；`GET /health` 返回 `{"status": "ok"}`。

- [ ] **Step 1: 写 requirements.txt**

```
fastapi==0.115.*
uvicorn==0.30.*
python-pptx==1.0.*
python-multipart==0.0.*
pydantic==2.*
pytest==8.*
httpx==0.27.*
```

- [ ] **Step 2: 写失败测试**

`ppt-editor-service/tests/test_health.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 3: 运行测试确认失败**

在 `ppt-editor-service/` 下：
```bash
pip install -r requirements.txt
python -m pytest tests/test_health.py -v
```
Expected: FAIL（`ModuleNotFoundError: No module named 'app'` 或 app 无 health 路由）

- [ ] **Step 4: 写最小实现**

`ppt-editor-service/app/__init__.py`: 空文件。
`ppt-editor-service/tests/__init__.py`: 空文件。
`ppt-editor-service/app/main.py`:
```python
from fastapi import FastAPI

app = FastAPI(title="PPT Editor Service")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: 运行测试确认通过**

```bash
python -m pytest tests/test_health.py -v
```
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add ppt-editor-service/
git commit -m "feat(ppt): FastAPI 骨架与健康检查"
```

---

### Task 2: ID 方案（IdIndex）

**Files:**
- Create: `ppt-editor-service/app/ids.py`
- Test: `ppt-editor-service/tests/conftest.py`
- Test: `ppt-editor-service/tests/test_ids.py`

**Interfaces:**
- Consumes: python-pptx 的 `Presentation`、`slide.shapes`、`slide.slide_id`。
- Produces:
  - `slide_id_for(index0:int) -> str`
  - `shape_short_id(order0:int) -> str`
  - `shape_id_for(slide_index0:int, shape_order0:int) -> str`
  - `class IdIndex(prs)`，方法：`slide(slide_id:str)->slide|None`、`shape(shape_id:str)->shape|None`、`register_temp_slide(temp_id:str, slide)->None`。

- [ ] **Step 1: 写共享 fixture（生成确定性测试 pptx）**

`ppt-editor-service/tests/conftest.py`:
```python
import pytest
from pptx import Presentation
from pptx.util import Inches


@pytest.fixture
def basic_pptx_path(tmp_path):
    """两页：标题页 + 要点页。"""
    prs = Presentation()
    s1 = prs.slides.add_slide(prs.slide_layouts[0])  # 标题幻灯片
    s1.shapes.title.text = "原标题"
    s1.placeholders[1].text = "原副标题"
    s2 = prs.slides.add_slide(prs.slide_layouts[1])  # 标题和内容
    s2.shapes.title.text = "要点页标题"
    s2.placeholders[1].text = "要点占位"
    p = tmp_path / "basic.pptx"
    prs.save(str(p))
    return str(p)


@pytest.fixture
def table_pptx_path(tmp_path):
    """一页：仅标题 + 一个 3x4 表格。"""
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[5])  # 仅标题
    gf = s.shapes.add_table(3, 4, Inches(1), Inches(2), Inches(8), Inches(3))
    gf.table.cell(0, 0).text = "季度"
    p = tmp_path / "table.pptx"
    prs.save(str(p))
    return str(p)
```

- [ ] **Step 2: 写失败测试**

`ppt-editor-service/tests/test_ids.py`:
```python
from pptx import Presentation
from app.ids import slide_id_for, shape_id_for, IdIndex


def test_id_encoding():
    assert slide_id_for(0) == "s1"
    assert shape_id_for(0, 2) == "s1_sh3"


def test_index_resolves_slide_and_shape(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    idx = IdIndex(prs)
    assert idx.slide("s1") is not None
    assert idx.slide("s99") is None
    # s1 第一个形状是标题占位符
    shp = idx.shape("s1_sh1")
    assert shp is not None
    assert shp.has_text_frame


def test_temp_slide_reference(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    idx = IdIndex(prs)
    src = idx.slide("s2")
    idx.register_temp_slide("d1", src)
    assert idx.slide("d1") is src
    # d1::sh1 解析为 d1 这页里第 1 个形状
    assert idx.shape("d1::sh1") is list(src.shapes)[0]
```

- [ ] **Step 3: 运行测试确认失败**

```bash
python -m pytest tests/test_ids.py -v
```
Expected: FAIL（`No module named 'app.ids'`）

- [ ] **Step 4: 写实现**

`ppt-editor-service/app/ids.py`:
```python
def slide_id_for(index0: int) -> str:
    return f"s{index0 + 1}"


def shape_short_id(order0: int) -> str:
    return f"sh{order0 + 1}"


def shape_id_for(slide_index0: int, shape_order0: int) -> str:
    return f"{slide_id_for(slide_index0)}_{shape_short_id(shape_order0)}"


class IdIndex:
    """解析与回写共用的确定性 ID → python-pptx 对象映射。

    在一次 /apply 会话内对内存中的同一个 Presentation 操作；
    dup_slide 产生的副本通过 register_temp_slide 注册临时页 ID。
    """

    def __init__(self, prs):
        self.prs = prs
        self._slides = {}        # slide_id -> slide
        self._shapes = {}        # shape_id -> shape
        self._temp_slides = {}   # temp_id -> slide
        for si, slide in enumerate(prs.slides):
            sid = slide_id_for(si)
            self._slides[sid] = slide
            for oi, shp in enumerate(slide.shapes):
                self._shapes[shape_id_for(si, oi)] = shp

    def slide(self, slide_id):
        if slide_id in self._temp_slides:
            return self._temp_slides[slide_id]
        return self._slides.get(slide_id)

    def register_temp_slide(self, temp_id, slide):
        self._temp_slides[temp_id] = slide

    def shape(self, shape_id):
        if "::" in shape_id:
            temp_id, short = shape_id.split("::", 1)
            slide = self._temp_slides.get(temp_id)
            if slide is None:
                return None
            try:
                order0 = int(short[2:]) - 1  # "sh2" -> 1
            except ValueError:
                return None
            shapes = list(slide.shapes)
            if 0 <= order0 < len(shapes):
                return shapes[order0]
            return None
        return self._shapes.get(shape_id)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
python -m pytest tests/test_ids.py -v
```
Expected: PASS（3 passed）

- [ ] **Step 6: 提交**

```bash
git add ppt-editor-service/app/ids.py ppt-editor-service/tests/conftest.py ppt-editor-service/tests/test_ids.py
git commit -m "feat(ppt): 确定性 ID 方案与 IdIndex 映射"
```

---

### Task 3: 解析器（pptx → JSON）

**Files:**
- Create: `ppt-editor-service/app/parser.py`
- Test: `ppt-editor-service/tests/test_parser.py`

**Interfaces:**
- Consumes: `app.ids.shape_id_for`、`slide_id_for`。
- Produces:
  - `parse_presentation(prs) -> dict`，结构 `{"slide_size": {"width","height"}, "slides": [...]}`。
  - 单页 `{"slide_id","index","layout_name","shapes":[...]}`。
  - 单形状 `{"shape_id","type","name","ph_type","pos":{x,y,w,h}}`，文本框另含 `text`、`style`，表格另含 `table`。
  - `type ∈ {"text","table","picture","chart","other"}`；`style = {"font","size","bold","color","align"}`；`table = {"rows","cols","cells":[{"r","c","text"}]}`。

- [ ] **Step 1: 写失败测试**

`ppt-editor-service/tests/test_parser.py`:
```python
from pptx import Presentation
from app.parser import parse_presentation


def test_parse_basic_structure(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    doc = parse_presentation(prs)
    assert doc["slide_size"]["width"] > 0
    assert len(doc["slides"]) == 2

    s1 = doc["slides"][0]
    assert s1["slide_id"] == "s1"
    assert s1["index"] == 0
    assert isinstance(s1["layout_name"], str)

    title = s1["shapes"][0]
    assert title["shape_id"] == "s1_sh1"
    assert title["type"] == "text"
    assert title["ph_type"] == "title"
    assert title["text"] == "原标题"
    assert title["style"]["size"] is None or isinstance(title["style"]["size"], int)
    for k in ("x", "y", "w", "h"):
        assert k in title["pos"]


def test_parse_table(table_pptx_path):
    prs = Presentation(table_pptx_path)
    doc = parse_presentation(prs)
    tbl_shapes = [s for s in doc["slides"][0]["shapes"] if s["type"] == "table"]
    assert len(tbl_shapes) == 1
    t = tbl_shapes[0]["table"]
    assert t["rows"] == 3 and t["cols"] == 4
    assert {"r": 0, "c": 0, "text": "季度"} in t["cells"]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_parser.py -v
```
Expected: FAIL（`No module named 'app.parser'`）

- [ ] **Step 3: 写实现**

`ppt-editor-service/app/parser.py`:
```python
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.enum.text import PP_ALIGN

from .ids import slide_id_for, shape_id_for

_ALIGN = {
    PP_ALIGN.LEFT: "left",
    PP_ALIGN.CENTER: "center",
    PP_ALIGN.RIGHT: "right",
    PP_ALIGN.JUSTIFY: "justify",
}


def _shape_kind(shape):
    if shape.has_table:
        return "table"
    if getattr(shape, "has_chart", False):
        return "chart"
    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
        return "picture"
    if shape.has_text_frame:
        return "text"
    return "other"


def _ph_type(shape):
    if not shape.is_placeholder:
        return None
    t = shape.placeholder_format.type
    if t in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE):
        return "title"
    if t == PP_PLACEHOLDER.SUBTITLE:
        return "subtitle"
    if t in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT):
        return "body"
    return str(t).split()[0].lower()


def _pos(shape):
    def emu(v):
        return int(v) if v is not None else None
    return {"x": emu(shape.left), "y": emu(shape.top),
            "w": emu(shape.width), "h": emu(shape.height)}


def _style(shape):
    tf = shape.text_frame
    para = tf.paragraphs[0]
    run = para.runs[0] if para.runs else None
    font = run.font if run else para.font
    color = None
    try:
        if font.color and font.color.type is not None:
            color = "#" + str(font.color.rgb)
    except Exception:
        color = None
    return {
        "font": font.name,
        "size": int(font.size.pt) if font.size else None,
        "bold": bool(font.bold) if font.bold is not None else False,
        "color": color,
        "align": _ALIGN.get(para.alignment),
    }


def _table(shape):
    t = shape.table
    rows = len(t.rows)
    cols = len(t.columns)
    cells = [{"r": r, "c": c, "text": t.cell(r, c).text}
             for r in range(rows) for c in range(cols)]
    return {"rows": rows, "cols": cols, "cells": cells}


def _parse_shape(shape, slide_index0, order0):
    kind = _shape_kind(shape)
    d = {
        "shape_id": shape_id_for(slide_index0, order0),
        "type": kind,
        "name": shape.name,
        "ph_type": _ph_type(shape),
        "pos": _pos(shape),
    }
    if shape.has_text_frame:
        d["text"] = shape.text_frame.text
        d["style"] = _style(shape)
    if kind == "table":
        d["table"] = _table(shape)
    return d


def _parse_slide(slide, index0):
    return {
        "slide_id": slide_id_for(index0),
        "index": index0,
        "layout_name": slide.slide_layout.name,
        "shapes": [_parse_shape(s, index0, i) for i, s in enumerate(slide.shapes)],
    }


def parse_presentation(prs):
    return {
        "slide_size": {"width": int(prs.slide_width), "height": int(prs.slide_height)},
        "slides": [_parse_slide(s, i) for i, s in enumerate(prs.slides)],
    }
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_parser.py -v
```
Expected: PASS（2 passed）

- [ ] **Step 5: 提交**

```bash
git add ppt-editor-service/app/parser.py ppt-editor-service/tests/test_parser.py
git commit -m "feat(ppt): pptx 解析为结构化 JSON"
```

---

### Task 4: 低层 pptx 操作（文本与表格）

**Files:**
- Create: `ppt-editor-service/app/pptx_ops.py`
- Test: `ppt-editor-service/tests/test_pptx_ops_text.py`

**Interfaces:**
- Consumes: python-pptx 形状/表格对象、`copy.deepcopy`。
- Produces：
  - `set_text_keep_style(text_frame, new_text:str) -> None`（保留首个 run 的字体样式）
  - `set_cell(table_shape, r:int, c:int, text:str) -> None`
  - `set_table_size(table_shape, rows:int, cols:int) -> None`

- [ ] **Step 1: 写失败测试**

`ppt-editor-service/tests/test_pptx_ops_text.py`:
```python
from pptx import Presentation
from app import pptx_ops


def test_set_text_keeps_bold(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    title = prs.slides[0].shapes[0]
    run = title.text_frame.paragraphs[0].runs[0]
    run.font.bold = True
    pptx_ops.set_text_keep_style(title.text_frame, "新标题")
    assert title.text_frame.text == "新标题"
    assert title.text_frame.paragraphs[0].runs[0].font.bold is True


def test_set_cell(table_pptx_path):
    prs = Presentation(table_pptx_path)
    tbl_shape = [s for s in prs.slides[0].shapes if s.has_table][0]
    pptx_ops.set_cell(tbl_shape, 1, 2, "85%")
    assert tbl_shape.table.cell(1, 2).text == "85%"


def test_set_table_size_add_and_remove_rows(table_pptx_path):
    prs = Presentation(table_pptx_path)
    tbl_shape = [s for s in prs.slides[0].shapes if s.has_table][0]
    pptx_ops.set_table_size(tbl_shape, rows=5, cols=4)
    assert len(tbl_shape.table.rows) == 5
    pptx_ops.set_table_size(tbl_shape, rows=2, cols=4)
    assert len(tbl_shape.table.rows) == 2


def test_set_table_size_add_col(table_pptx_path):
    prs = Presentation(table_pptx_path)
    tbl_shape = [s for s in prs.slides[0].shapes if s.has_table][0]
    pptx_ops.set_table_size(tbl_shape, rows=3, cols=6)
    assert len(tbl_shape.table.columns) == 6
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_pptx_ops_text.py -v
```
Expected: FAIL（`No module named 'app.pptx_ops'`）

- [ ] **Step 3: 写实现（文本与表格部分）**

`ppt-editor-service/app/pptx_ops.py`:
```python
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
    for tc in tr.tc_lst:
        for p in tc.iter_paragraphs():
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
        for tr in tbl.tr_lst[rows:]:
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
```

注意：`tr.tc_lst`、`tbl.tblGrid`、`grid.gridCol_lst`、`tc.iter_paragraphs()`、`p.r_lst` 均为 python-pptx oxml 生成的访问器。若 `_clear_tr_text` 的某访问器名不符，运行测试时按报错调整为等价访问（如用 `tc.txBody`）。

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_pptx_ops_text.py -v
```
Expected: PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git add ppt-editor-service/app/pptx_ops.py ppt-editor-service/tests/test_pptx_ops_text.py
git commit -m "feat(ppt): 文本/表格低层写入操作"
```

---

### Task 5: 低层 pptx 操作（复制/删除整页）

**Files:**
- Modify: `ppt-editor-service/app/pptx_ops.py`
- Test: `ppt-editor-service/tests/test_pptx_ops_slides.py`

**Interfaces:**
- Consumes: `prs.slides`、`prs.slides._sldIdLst`、`slide.slide_layout`、`slide.slide_id`、`shape._element`、`slide.shapes._spTree`。
- Produces:
  - `slide_index(prs, slide) -> int`
  - `duplicate_slide_after(prs, source_slide, count:int) -> list[slide]`（紧跟源页之后插入，按顺序返回新页）
  - `delete_slide(prs, slide) -> bool`

- [ ] **Step 1: 写失败测试**

`ppt-editor-service/tests/test_pptx_ops_slides.py`:
```python
from pptx import Presentation
from app import pptx_ops


def test_duplicate_after_keeps_order_and_content(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    src = prs.slides[1]  # 要点页
    news = pptx_ops.duplicate_slide_after(prs, src, 2)
    assert len(news) == 2
    assert len(prs.slides) == 4
    # 副本紧跟在源页（index 1）之后
    assert pptx_ops.slide_index(prs, news[0]) == 2
    assert pptx_ops.slide_index(prs, news[1]) == 3
    # 副本内容复制自源页标题
    assert news[0].shapes[0].text_frame.text == "要点页标题"


def test_delete_slide(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    target = prs.slides[0]
    assert pptx_ops.delete_slide(prs, target) is True
    assert len(prs.slides) == 1
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_pptx_ops_slides.py -v
```
Expected: FAIL（`module 'app.pptx_ops' has no attribute 'duplicate_slide_after'`）

- [ ] **Step 3: 追加实现到 pptx_ops.py**

在 `ppt-editor-service/app/pptx_ops.py` 末尾追加：
```python
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_pptx_ops_slides.py -v
```
Expected: PASS（2 passed）

- [ ] **Step 5: 提交**

```bash
git add ppt-editor-service/app/pptx_ops.py ppt-editor-service/tests/test_pptx_ops_slides.py
git commit -m "feat(ppt): 整页复制/删除操作"
```

---

### Task 6: 指令分发器（applier）

**Files:**
- Create: `ppt-editor-service/app/applier.py`
- Test: `ppt-editor-service/tests/test_applier.py`

**Interfaces:**
- Consumes: `app.ids.IdIndex`、`app.pptx_ops` 全部函数。
- Produces:
  - `class OpError(Exception)`
  - `apply_ops(prs, ops:list[dict]) -> tuple[int, list[dict]]`，返回 `(applied_count, rejected)`；`rejected` 每项 `{"index":int, "op":str|None, "reason":str}`。
  - 支持指令：`set_text`、`set_cell`、`set_table_size`、`dup_slide`、`del_slide`。指令按列表顺序执行。

- [ ] **Step 1: 写失败测试**

`ppt-editor-service/tests/test_applier.py`:
```python
from pptx import Presentation
from app.applier import apply_ops
from app.parser import parse_presentation


def test_set_text_applied(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    applied, rejected = apply_ops(prs, [
        {"op": "set_text", "shape_id": "s1_sh1", "text": "新标题"},
    ])
    assert applied == 1 and rejected == []
    assert prs.slides[0].shapes[0].text_frame.text == "新标题"


def test_dup_then_fill_copies(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    applied, rejected = apply_ops(prs, [
        {"op": "dup_slide", "slide_id": "s2", "count": 2, "as": ["d1", "d2"]},
        {"op": "set_text", "shape_id": "d1::sh1", "text": "要点一"},
        {"op": "set_text", "shape_id": "d2::sh1", "text": "要点二"},
    ])
    assert applied == 3 and rejected == []
    assert len(prs.slides) == 4
    assert prs.slides[2].shapes[0].text_frame.text == "要点一"
    assert prs.slides[3].shapes[0].text_frame.text == "要点二"


def test_bad_id_rejected_but_others_apply(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    applied, rejected = apply_ops(prs, [
        {"op": "set_text", "shape_id": "s9_sh9", "text": "x"},
        {"op": "set_text", "shape_id": "s1_sh1", "text": "ok"},
    ])
    assert applied == 1
    assert len(rejected) == 1
    assert rejected[0]["index"] == 0
    assert "不存在" in rejected[0]["reason"]
    assert prs.slides[0].shapes[0].text_frame.text == "ok"


def test_del_slide(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    applied, rejected = apply_ops(prs, [{"op": "del_slide", "slide_id": "s1"}])
    assert applied == 1 and rejected == []
    assert len(prs.slides) == 1
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_applier.py -v
```
Expected: FAIL（`No module named 'app.applier'`）

- [ ] **Step 3: 写实现**

`ppt-editor-service/app/applier.py`:
```python
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_applier.py -v
```
Expected: PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git add ppt-editor-service/app/applier.py ppt-editor-service/tests/test_applier.py
git commit -m "feat(ppt): 编辑指令分发器与逐条拒绝机制"
```

---

### Task 7: 存储层

**Files:**
- Create: `ppt-editor-service/app/storage.py`
- Test: `ppt-editor-service/tests/test_storage.py`

**Interfaces:**
- Consumes: `os`、`uuid`。
- Produces:
  - `class Storage(root:str)`
  - `.new_doc(data:bytes) -> str`（生成 doc_id，写入 `source.pptx`）
  - `.source_path(doc_id) -> str`
  - `.output_path(doc_id) -> str`（`{doc_id}-out.pptx`）
  - `.exists(doc_id) -> bool`

- [ ] **Step 1: 写失败测试**

`ppt-editor-service/tests/test_storage.py`:
```python
import os
from app.storage import Storage


def test_new_doc_persists_source(tmp_path):
    st = Storage(str(tmp_path))
    doc_id = st.new_doc(b"hello-bytes")
    assert st.exists(doc_id)
    with open(st.source_path(doc_id), "rb") as f:
        assert f.read() == b"hello-bytes"
    assert st.output_path(doc_id).endswith(f"{doc_id}-out.pptx")


def test_missing_doc(tmp_path):
    st = Storage(str(tmp_path))
    assert st.exists("nope") is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_storage.py -v
```
Expected: FAIL（`No module named 'app.storage'`）

- [ ] **Step 3: 写实现**

`ppt-editor-service/app/storage.py`:
```python
import os
import uuid


class Storage:
    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _dir(self, doc_id):
        return os.path.join(self.root, doc_id)

    def new_doc(self, data: bytes) -> str:
        doc_id = uuid.uuid4().hex[:8]
        os.makedirs(self._dir(doc_id), exist_ok=True)
        with open(self.source_path(doc_id), "wb") as f:
            f.write(data)
        return doc_id

    def source_path(self, doc_id):
        return os.path.join(self._dir(doc_id), "source.pptx")

    def output_path(self, doc_id):
        return os.path.join(self._dir(doc_id), f"{doc_id}-out.pptx")

    def exists(self, doc_id):
        return os.path.isdir(self._dir(doc_id))
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_storage.py -v
```
Expected: PASS（2 passed）

- [ ] **Step 5: 提交**

```bash
git add ppt-editor-service/app/storage.py ppt-editor-service/tests/test_storage.py
git commit -m "feat(ppt): 本地盘存储层"
```

---

### Task 8: HTTP 接口（/parse、/apply、/files）

**Files:**
- Modify: `ppt-editor-service/app/main.py`
- Create: `ppt-editor-service/app/models.py`
- Test: `ppt-editor-service/tests/test_api.py`

**Interfaces:**
- Consumes: `app.storage.Storage`、`app.parser.parse_presentation`、`app.applier.apply_ops`、`app.models.ApplyRequest`、python-pptx `Presentation`、FastAPI `UploadFile`/`HTTPException`/`FileResponse`。
- Produces:
  - `POST /parse`（multipart `file`）→ `{doc_id, slide_size, slides}`，非法文件 400。
  - `POST /apply`（JSON `{doc_id, ops}`）→ `{download_url, applied, rejected}`，doc_id 不存在 404，输出校验失败 500。
  - `GET /files/{name}` → pptx 二进制附件。

- [ ] **Step 1: 写 pydantic 模型**

`ppt-editor-service/app/models.py`:
```python
from typing import Any
from pydantic import BaseModel


class ApplyRequest(BaseModel):
    doc_id: str
    ops: list[dict[str, Any]]
```

- [ ] **Step 2: 写失败测试**

`ppt-editor-service/tests/test_api.py`:
```python
import io
from pptx import Presentation
from fastapi.testclient import TestClient
import app.main as main_mod
from app.main import app


def _setup_storage(tmp_path):
    from app.storage import Storage
    main_mod.storage = Storage(str(tmp_path))


def test_parse_then_apply_then_download(tmp_path, basic_pptx_path):
    _setup_storage(tmp_path)
    client = TestClient(app)

    with open(basic_pptx_path, "rb") as f:
        resp = client.post("/parse", files={"file": ("t.pptx", f, "application/octet-stream")})
    assert resp.status_code == 200
    doc = resp.json()
    doc_id = doc["doc_id"]
    assert doc["slides"][0]["shapes"][0]["shape_id"] == "s1_sh1"

    resp2 = client.post("/apply", json={
        "doc_id": doc_id,
        "ops": [{"op": "set_text", "shape_id": "s1_sh1", "text": "改后标题"}],
    })
    assert resp2.status_code == 200
    body = resp2.json()
    assert body["applied"] == 1 and body["rejected"] == []
    name = body["download_url"].split("/files/")[1]

    resp3 = client.get(f"/files/{name}")
    assert resp3.status_code == 200
    prs = Presentation(io.BytesIO(resp3.content))
    assert prs.slides[0].shapes[0].text_frame.text == "改后标题"


def test_parse_rejects_garbage(tmp_path):
    _setup_storage(tmp_path)
    client = TestClient(app)
    resp = client.post("/parse", files={"file": ("x.pptx", io.BytesIO(b"not a pptx"), "application/octet-stream")})
    assert resp.status_code == 400


def test_apply_unknown_doc(tmp_path):
    _setup_storage(tmp_path)
    client = TestClient(app)
    resp = client.post("/apply", json={"doc_id": "ghost", "ops": []})
    assert resp.status_code == 404
```

- [ ] **Step 3: 运行测试确认失败**

```bash
python -m pytest tests/test_api.py -v
```
Expected: FAIL（/parse、/apply、/files 未定义）

- [ ] **Step 4: 写实现（覆盖 main.py）**

`ppt-editor-service/app/main.py`:
```python
import os

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pptx import Presentation

from .storage import Storage
from .parser import parse_presentation
from .applier import apply_ops
from .models import ApplyRequest

app = FastAPI(title="PPT Editor Service")
storage = Storage(os.environ.get("PPT_STORAGE", "./storage"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse")
async def parse_endpoint(file: UploadFile = File(...)):
    data = await file.read()
    doc_id = storage.new_doc(data)
    try:
        prs = Presentation(storage.source_path(doc_id))
    except Exception:
        raise HTTPException(status_code=400, detail="无法解析 pptx 文件")
    result = parse_presentation(prs)
    result["doc_id"] = doc_id
    return result


@app.post("/apply")
def apply_endpoint(req: ApplyRequest):
    if not storage.exists(req.doc_id):
        raise HTTPException(status_code=404, detail="doc_id 不存在")
    prs = Presentation(storage.source_path(req.doc_id))
    applied, rejected = apply_ops(prs, req.ops)
    out = storage.output_path(req.doc_id)
    prs.save(out)
    try:
        Presentation(out)  # 输出有效性校验
    except Exception:
        raise HTTPException(status_code=500, detail="生成的 pptx 校验失败")
    name = os.path.basename(out)
    return {"download_url": f"/files/{name}", "applied": applied, "rejected": rejected}


@app.get("/files/{name}")
def download(name: str):
    doc_id = name.split("-out")[0]
    path = storage.output_path(doc_id)
    if not (os.path.basename(path) == name and os.path.isfile(path)):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        path,
        filename=name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
```

- [ ] **Step 5: 运行测试确认通过**

```bash
python -m pytest tests/test_api.py -v
```
Expected: PASS（3 passed）

- [ ] **Step 6: 全量回归 + 提交**

```bash
python -m pytest -v
git add ppt-editor-service/app/main.py ppt-editor-service/app/models.py ppt-editor-service/tests/test_api.py
git commit -m "feat(ppt): /parse /apply /files HTTP 接口"
```
Expected: 全部 PASS。

---

### Task 9: 机械链路集成验证（不接 LLM）

**Files:**
- Create: `ppt-editor-service/tests/test_integration.py`
- Create: `ppt-editor-service/scripts/demo_roundtrip.py`

**Interfaces:**
- Consumes: 全部已建模块。
- Produces:
  - 端到端集成测试：parse → 手写 ops（含 set_text + dup_slide + del_slide + set_cell）→ apply → 重新解析断言。
  - `scripts/demo_roundtrip.py`：可手动运行的演示脚本，输入一个 pptx 路径，输出改写后的 pptx。

- [ ] **Step 1: 写集成测试**

`ppt-editor-service/tests/test_integration.py`:
```python
from pptx import Presentation
from app.parser import parse_presentation
from app.applier import apply_ops


def test_full_mechanical_roundtrip(basic_pptx_path):
    prs = Presentation(basic_pptx_path)
    doc = parse_presentation(prs)
    assert len(doc["slides"]) == 2

    # 手写一份「改标题 + 复制要点页3份分别填内容 + 删原首页」的指令
    ops = [
        {"op": "dup_slide", "slide_id": "s2", "count": 3, "as": ["d1", "d2", "d3"]},
        {"op": "set_text", "shape_id": "d1::sh1", "text": "要点一"},
        {"op": "set_text", "shape_id": "d2::sh1", "text": "要点二"},
        {"op": "set_text", "shape_id": "d3::sh1", "text": "要点三"},
        {"op": "del_slide", "slide_id": "s1"},
    ]
    applied, rejected = apply_ops(prs, ops)
    assert rejected == []
    assert applied == 5

    # 重新解析验证最终结构
    doc2 = parse_presentation(prs)
    titles = [s["shapes"][0]["text"] for s in doc2["slides"]]
    # 原首页已删，剩：原要点页 + 3 张副本
    assert "要点一" in titles and "要点二" in titles and "要点三" in titles
    assert len(doc2["slides"]) == 4
```

- [ ] **Step 2: 运行测试确认通过**

```bash
python -m pytest tests/test_integration.py -v
```
Expected: PASS（先写测试即应通过，因为依赖的模块已在前序任务完成；若失败说明前序任务有缺陷，回到对应任务修复）

- [ ] **Step 3: 写演示脚本**

`ppt-editor-service/scripts/demo_roundtrip.py`:
```python
"""手动演示：python demo_roundtrip.py input.pptx output.pptx
仅改第一页第一个文本框，验证机械链路。"""
import sys
from pptx import Presentation
from app.parser import parse_presentation
from app.applier import apply_ops


def main():
    src, dst = sys.argv[1], sys.argv[2]
    prs = Presentation(src)
    doc = parse_presentation(prs)
    first = doc["slides"][0]["shapes"][0]["shape_id"]
    applied, rejected = apply_ops(prs, [
        {"op": "set_text", "shape_id": first, "text": "DEMO 改写成功"},
    ])
    prs.save(dst)
    print(f"applied={applied} rejected={rejected} -> {dst}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 手动跑一次演示脚本**

```bash
cd ppt-editor-service
python -c "from tests.conftest import *; import tempfile"  # 仅确认导入无误（可跳过）
# 用任意真实模板：
python scripts/demo_roundtrip.py path/to/your-template.pptx /tmp/out.pptx
```
Expected: 打印 `applied=1 rejected=[] -> /tmp/out.pptx`，打开 out.pptx 第一页首个文本框已变为 "DEMO 改写成功"，其余样式不变。

- [ ] **Step 5: 提交**

```bash
git add ppt-editor-service/tests/test_integration.py ppt-editor-service/scripts/demo_roundtrip.py
git commit -m "test(ppt): 机械链路端到端集成验证 + 演示脚本"
```

---

### Task 10: Dify 工作流接入（配置 + LLM Prompt）

**Files:**
- Create: `ppt-editor-service/README.md`
- Create: `docs/superpowers/dify-workflow-ppt-edit.md`

**Interfaces:**
- Consumes: 已部署运行的 PPT 服务（`/parse`、`/apply`）。
- Produces：Dify 工作流的节点配置说明 + LLM 节点 system/user prompt 全文 + 校验代码节点片段。本任务为配置文档交付，无自动化测试，验收靠真实 Dify 端到端跑通。

- [ ] **Step 1: 写服务 README（部署说明）**

`ppt-editor-service/README.md`:
```markdown
# PPT Editor Service

把 PPT 模板解析为带 ID 的 JSON，并按编辑指令回写 pptx。

## 运行
pip install -r requirements.txt
PPT_STORAGE=./storage uvicorn app.main:app --host 0.0.0.0 --port 8000

## 接口
- POST /parse  (multipart file) -> {doc_id, slide_size, slides}
- POST /apply  ({doc_id, ops})  -> {download_url, applied, rejected}
- GET  /files/{name}            -> pptx 附件

## 指令集（v1）
set_text / set_cell / set_table_size / dup_slide / del_slide
（详见 docs/superpowers/specs/2026-06-18-ppt-template-llm-edit-design.md）
```

- [ ] **Step 2: 写 Dify 工作流配置文档**

`docs/superpowers/dify-workflow-ppt-edit.md`:
```markdown
# Dify 工作流：PPT 模板 LLM 编辑

## 节点串联
[开始] file(文件) + user_brief(文本)
  → [HTTP-1 解析] POST {SVC}/parse，body 传 file
  → [LLM 生成指令] 输入 parse_result.slides + user_brief
  → [代码-校验] 解析 LLM 输出为 JSON、补 doc_id
  → [HTTP-2 回写] POST {SVC}/apply，body = {doc_id, ops}
  → [结束] 返回 download_url（+ rejected 提示）

## HTTP-1 解析节点
- Method: POST，URL: {SVC}/parse
- Body: form-data，key=file，value=开始节点的文件变量
- 输出变量：parse_result（含 doc_id、slides）

## LLM 节点 — System Prompt（原文照抄）
你是PPT编辑指令生成器。你只能输出JSON，包含一个ops数组，不要输出任何解释文字。
可用指令仅5种：set_text / set_cell / set_table_size / dup_slide / del_slide。
铁律：
1. shape_id/slide_id 必须来自输入JSON，严禁编造。
2. 复制页并填内容时，必须先 dup_slide，再用 as 里的临时页ID引用副本里的形状，格式为 临时页ID::形状短ID（如 d1::sh2）。
3. ops 按数组顺序执行，dup_slide 必须排在引用其副本的指令之前。
4. 不改样式、不改坐标、不动图片。只允许改文字、表格数据、增删整页。
5. 识别语义靠 ph_type / name / 位置(pos) / 字号(style.size)。ph_type=title 是标题，多个并列同样式的 body 框所在页通常是可重复的要点页。

输出格式示例：
{"ops":[
  {"op":"set_text","shape_id":"s1_sh1","text":"2026 产品发布会"},
  {"op":"dup_slide","slide_id":"s2","count":3,"as":["d1","d2","d3"]},
  {"op":"set_text","shape_id":"d1::sh1","text":"要点一"},
  {"op":"set_text","shape_id":"d2::sh1","text":"要点二"},
  {"op":"set_text","shape_id":"d3::sh1","text":"要点三"},
  {"op":"del_slide","slide_id":"s3"}
]}

## LLM 节点 — User Prompt
模板结构（JSON）：
{{#parse_result.slides#}}
用户需求：
{{#start.user_brief#}}
请只输出 ops 的 JSON。

## 代码-校验节点（Python）
def main(llm_text: str, doc_id: str) -> dict:
    import json, re
    s = llm_text.strip()
    m = re.search(r"\{.*\}", s, re.S)  # 容错：抠出第一个 JSON 对象
    if not m:
        return {"valid": False, "payload": {}}
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return {"valid": False, "payload": {}}
    ops = obj.get("ops", [])
    return {"valid": True, "payload": {"doc_id": doc_id, "ops": ops}}

- 若 valid=False：用条件分支走「失败提示」结束（提示用户重试或换模板）。
- 若 valid=True：把 payload 传给 HTTP-2。

## HTTP-2 回写节点
- Method: POST，URL: {SVC}/apply
- Body: JSON = 代码节点的 payload（{doc_id, ops}）
- 输出：download_url、applied、rejected

## 结束节点
- 返回 download_url；若 rejected 非空，附「部分指令未生效」提示并列出 rejected。
```

- [ ] **Step 3: 端到端人工验收**

部署服务后，在 Dify 里：上传一个真实模板 + 填写需求（如「做一份含 4 个产品卖点的介绍」）→ 跑完工作流 → 下载 pptx。
Expected（肉眼验收）：
- 样式与原模板一致（字体/配色/版式未走样）；
- 卖点页数与需求一致（如 4 页）；
- 文案为新生成内容；
- 如有 rejected，结束节点有提示。

- [ ] **Step 4: 提交**

```bash
git add ppt-editor-service/README.md docs/superpowers/dify-workflow-ppt-edit.md
git commit -m "docs(ppt): 服务 README 与 Dify 工作流接入配置"
```

---

## Self-Review

**Spec 覆盖核对：**
- §2 架构（服务/Dify/LLM 三组件）→ Task 1/8（服务）、Task 10（Dify+LLM）。✓
- §3 JSON 数据结构（slide/shape/style/table/ph_type/pos）→ Task 3。✓
- §4 指令 schema（5 条 + 临时 ID + 顺序执行）→ Task 4/5/6（实现）、Task 10（prompt 约束）。✓
- §5 接口（/parse、/apply 含 rejected、/files、doc_id 串联、另存输出）→ Task 7/8。✓
- §6 Dify 编排 + prompt + 校验代码节点 → Task 10。✓
- §7 错误处理（局部拒绝、非法文件、输出校验、非法 JSON 兜底）→ Task 6（rejected）、Task 8（400/500）、Task 10（校验节点）。✓
- §8 测试（解析/回写/往返/校验四层 + LLM 评估 + 端到端）→ Task 3/4/5/6/9（机械四层）、Task 10 Step3（端到端）。LLM 评估用例为人工抽检，列入 Task 10 验收。✓
- §9 实现顺序（先机械后智能）→ Task 1-9 机械、Task 10 接 LLM。✓
- §10 v2 待办 → 明确不在本计划范围。✓

**Placeholder 扫描：** 无 TBD/TODO；每个代码步骤均含完整代码。Task 4 对 oxml 访问器名做了「按报错调整」的提示，属已知 python-pptx 版本差异的合理兜底，非占位符。

**类型一致性：** `apply_ops` 返回 `(applied, rejected)` 在 Task 6 定义、Task 8/9 一致使用；`Storage` 方法名 `new_doc/source_path/output_path/exists` 在 Task 7 定义、Task 8 一致；`IdIndex.slide/shape/register_temp_slide` 在 Task 2 定义、Task 6 一致；`duplicate_slide_after/delete_slide/slide_index` 在 Task 5 定义、Task 6 一致。✓
