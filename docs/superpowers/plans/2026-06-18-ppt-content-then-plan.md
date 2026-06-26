# PPT 内容先行 + 计划映射（B2） Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `/parse` 额外返回精简 `skeleton`，新增服务端 `/apply_plan` 端点把「内容计划 plan」确定性展开成已有 5 条 ops 再回写；并把 Dify 工作流从单 LLM 改成「LLM-A 创作内容 → LLM-B 映射 → /apply_plan」，解决「输出内容太少且不完整」。

**Architecture:** 在现有 `ppt-editor-service`（FastAPI + python-pptx）上演进。新增 `app/skeleton.py`（slides→骨架）和 `app/plan.py`（plan→ops 纯函数展开器）；`/apply_plan` = `expand_plan` + 复用现有 `apply_ops`（一行不改）。Dify 侧拆两个 LLM，机械活全部回到有测试的服务端。

**Tech Stack:** Python 3.11+、FastAPI、python-pptx、pytest、FastAPI TestClient、Dify 工作流 DSL。

## Global Constraints

- 工作目录：`ppt-editor-service/`，应用包 `app/`，测试 `tests/`，从该目录内跑 `python -m pytest`。
- 复用且不修改：`app/applier.py`（`apply_ops`、`OpError`）、`app/pptx_ops.py`、`app/ids.py`、`app/parser.py`（`parse_presentation`）、`app/storage.py`（`Storage`、`valid_doc_id`）。
- 确定性 ID 不变：slide `s{n}`、shape `s{n}_sh{m}`、临时 `tmp::sh`。展开器生成的临时页 ID 用 `{slide_id}__r{i}`（i 从 1 起），副本形状引用 `{临时页ID}::{短ID}`，短 ID = shape_id 最后一段（`s2_sh1`→`sh1`）。
- 5 条指令集不变：set_text / set_cell / set_table_size / dup_slide / del_slide。
- skeleton 槽位 role 规则（纯机械）：`ph_type=title→title`、`subtitle→subtitle`、`body→body`、`type=table→table`、`type∈{picture,chart}→media`、其余 `other`。页 role 优先级：有 table 槽→`table`；含 title 且 subtitle→`cover`；含 title 且 body→`content`；其余 `generic`。
- 展开器不抛异常、不中断：空 items 跳过、畸形 shape_id 用原值兜底、未知 kind 跳过并记 warning；非法 op 交给 `apply_ops` 逐条 reject。
- `/apply_plan` 沿用安全约束：`valid_doc_id` + `storage.exists` 校验（否则 404）；从 `source.pptx` 出发，另存 `{doc_id}-out.pptx`，重开校验失败→500。
- 本计划在分支 `feat/ppt-editor-service` 上继续提交。

---

### Task 1: skeleton 骨架（builder + 接入 /parse）

**Files:**
- Create: `ppt-editor-service/app/skeleton.py`
- Modify: `ppt-editor-service/app/main.py`（`/parse` 返回值加 `skeleton`）
- Test: `ppt-editor-service/tests/test_skeleton.py`
- Test: `ppt-editor-service/tests/test_api.py`（追加一条 parse 含 skeleton 的断言）

**Interfaces:**
- Consumes: `app.parser.parse_presentation(prs) -> dict`（含 `slides`，每页 `shapes`，shape 含 `shape_id/type/ph_type/text`，表格含 `table:{rows,cols}`）。
- Produces: `build_skeleton(parsed: dict) -> dict`，结构 `{"slides":[{"slide_id","role","slots":[{"shape_id","role","type","sample?","rows?","cols?"}]}]}`。`/parse` 响应新增 `skeleton` 字段。

- [ ] **Step 1: 写失败测试**

`ppt-editor-service/tests/test_skeleton.py`:
```python
from pptx import Presentation
from app.parser import parse_presentation
from app.skeleton import build_skeleton


def test_skeleton_cover_and_content(basic_pptx_path):
    parsed = parse_presentation(Presentation(basic_pptx_path))
    sk = build_skeleton(parsed)
    assert len(sk["slides"]) == 2
    s1 = sk["slides"][0]
    assert s1["slide_id"] == "s1"
    assert s1["role"] == "cover"            # title + subtitle
    roles = {slot["role"] for slot in s1["slots"]}
    assert "title" in roles and "subtitle" in roles
    # 标题槽 shape_id 与解析一致
    title_slot = next(s for s in s1["slots"] if s["role"] == "title")
    assert title_slot["shape_id"] == "s1_sh1"
    assert sk["slides"][1]["role"] == "content"   # title + body


def test_skeleton_table_page(table_pptx_path):
    parsed = parse_presentation(Presentation(table_pptx_path))
    sk = build_skeleton(parsed)
    page = sk["slides"][0]
    assert page["role"] == "table"
    tslot = next(s for s in page["slots"] if s["role"] == "table")
    assert tslot["type"] == "table"
    assert tslot["rows"] == 3 and tslot["cols"] == 4
```

- [ ] **Step 2: 运行确认失败**

```bash
python -m pytest tests/test_skeleton.py -v
```
Expected: FAIL（`No module named 'app.skeleton'`）

- [ ] **Step 3: 写实现**

`ppt-editor-service/app/skeleton.py`:
```python
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
```

- [ ] **Step 4: 运行确认通过**

```bash
python -m pytest tests/test_skeleton.py -v
```
Expected: PASS（2 passed）

- [ ] **Step 5: 接入 /parse**

在 `ppt-editor-service/app/main.py` 顶部 import 区加：
```python
from .skeleton import build_skeleton
```
在 `parse_endpoint` 里，`result["doc_id"] = doc_id` 之后、`return result` 之前加一行：
```python
    result["skeleton"] = build_skeleton(result)
```

- [ ] **Step 6: 追加 API 测试**

在 `ppt-editor-service/tests/test_api.py` 末尾追加：
```python
def test_parse_returns_skeleton(tmp_path, basic_pptx_path):
    import app.main as main_mod
    from app.storage import Storage
    main_mod.storage = Storage(str(tmp_path))
    from fastapi.testclient import TestClient
    client = TestClient(main_mod.app)
    with open(basic_pptx_path, "rb") as f:
        resp = client.post("/parse", files={"file": ("t.pptx", f, "application/octet-stream")})
    assert resp.status_code == 200
    sk = resp.json()["skeleton"]
    assert sk["slides"][0]["role"] == "cover"
```

- [ ] **Step 7: 跑全量 + 提交**

```bash
python -m pytest -v
git add ppt-editor-service/app/skeleton.py ppt-editor-service/app/main.py ppt-editor-service/tests/test_skeleton.py ppt-editor-service/tests/test_api.py
git commit -m "feat(ppt): /parse 返回精简 skeleton 骨架"
```
Expected: 全部 PASS。

---

### Task 2: plan→ops 展开器（app/plan.py）

**Files:**
- Create: `ppt-editor-service/app/plan.py`
- Test: `ppt-editor-service/tests/test_plan.py`

**Interfaces:**
- Consumes: `structure`（`parse_presentation` 的返回 dict，用于查表格当前行列）。
- Produces: `expand_plan(plan: list, structure: dict) -> tuple[list, list]`，返回 `(ops, warnings)`。`ops` 是 set_text/set_cell/set_table_size/dup_slide/del_slide 的 dict 列表；`warnings` 是字符串列表。
  - fill → 每个 field 一条 `set_text`
  - repeat（items 非空）→ 一条 `dup_slide`(count=len, as=`{slide_id}__r{i}`) + 每个副本每个 field 一条 `set_text`(shape_id=`{临时页}::{短ID}`)
  - table（rows 非空）→ 当前尺寸≠目标则先 `set_table_size`，再逐格 `set_cell`
  - drop → 一条 `del_slide`

- [ ] **Step 1: 写失败测试**

`ppt-editor-service/tests/test_plan.py`:
```python
from app.plan import expand_plan


def test_fill():
    ops, warn = expand_plan(
        [{"kind": "fill", "slide_id": "s1", "fields": {"s1_sh1": "标题", "s1_sh2": "副"}}], {})
    assert warn == []
    assert {"op": "set_text", "shape_id": "s1_sh1", "text": "标题"} in ops
    assert {"op": "set_text", "shape_id": "s1_sh2", "text": "副"} in ops


def test_repeat_generates_dup_and_temp_ids():
    plan = [{"kind": "repeat", "slide_id": "s2", "items": [
        {"s2_sh1": "A1", "s2_sh2": "A2"},
        {"s2_sh1": "B1", "s2_sh2": "B2"},
    ]}]
    ops, warn = expand_plan(plan, {})
    assert ops[0] == {"op": "dup_slide", "slide_id": "s2", "count": 2, "as": ["s2__r1", "s2__r2"]}
    # dup 在所有填充之前
    assert ops[0]["op"] == "dup_slide"
    assert {"op": "set_text", "shape_id": "s2__r1::sh1", "text": "A1"} in ops
    assert {"op": "set_text", "shape_id": "s2__r2::sh2", "text": "B2"} in ops


def test_repeat_empty_items_skipped():
    ops, warn = expand_plan([{"kind": "repeat", "slide_id": "s2", "items": []}], {})
    assert ops == [] and warn == []


def test_repeat_malformed_shape_id_falls_back():
    ops, _ = expand_plan([{"kind": "repeat", "slide_id": "s2",
                           "items": [{"weird": "X"}]}], {})
    assert {"op": "set_text", "shape_id": "s2__r1::weird", "text": "X"} in ops


def test_table_resizes_when_dims_differ():
    structure = {"slides": [{"shapes": [
        {"shape_id": "s3_sh4", "type": "table", "table": {"rows": 3, "cols": 4}}]}]}
    plan = [{"kind": "table", "shape_id": "s3_sh4",
             "rows": [["指标", "前", "后"], ["响应", "30s", "3s"]]}]
    ops, _ = expand_plan(plan, structure)
    assert ops[0] == {"op": "set_table_size", "shape_id": "s3_sh4", "rows": 2, "cols": 3}
    assert {"op": "set_cell", "shape_id": "s3_sh4", "r": 0, "c": 0, "text": "指标"} in ops
    assert {"op": "set_cell", "shape_id": "s3_sh4", "r": 1, "c": 2, "text": "3s"} in ops


def test_table_no_resize_when_dims_match():
    structure = {"slides": [{"shapes": [
        {"shape_id": "s3_sh4", "type": "table", "table": {"rows": 1, "cols": 2}}]}]}
    ops, _ = expand_plan([{"kind": "table", "shape_id": "s3_sh4",
                           "rows": [["a", "b"]]}], structure)
    assert all(o["op"] != "set_table_size" for o in ops)


def test_drop():
    ops, _ = expand_plan([{"kind": "drop", "slide_id": "s4"}], {})
    assert ops == [{"op": "del_slide", "slide_id": "s4"}]


def test_unknown_kind_warns():
    ops, warn = expand_plan([{"kind": "frobnicate"}], {})
    assert ops == []
    assert any("frobnicate" in w for w in warn)
```

- [ ] **Step 2: 运行确认失败**

```bash
python -m pytest tests/test_plan.py -v
```
Expected: FAIL（`No module named 'app.plan'`）

- [ ] **Step 3: 写实现**

`ppt-editor-service/app/plan.py`:
```python
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
```

- [ ] **Step 4: 运行确认通过**

```bash
python -m pytest tests/test_plan.py -v
```
Expected: PASS（8 passed）

- [ ] **Step 5: 提交**

```bash
git add ppt-editor-service/app/plan.py ppt-editor-service/tests/test_plan.py
git commit -m "feat(ppt): plan→ops 确定性展开器"
```

---

### Task 3: /apply_plan 端点 + 集成测试 + 演示脚本

**Files:**
- Modify: `ppt-editor-service/app/models.py`（加 `ApplyPlanRequest`）
- Modify: `ppt-editor-service/app/main.py`（加 `/apply_plan`）
- Create: `ppt-editor-service/scripts/demo_plan.py`
- Test: `ppt-editor-service/tests/test_api_plan.py`

**Interfaces:**
- Consumes: `app.plan.expand_plan`、`app.applier.apply_ops`、`app.parser.parse_presentation`、`app.storage.valid_doc_id`/`Storage`、`app.models.ApplyPlanRequest`。
- Produces: `POST /apply_plan`（JSON `{doc_id, plan}`）→ `{download_url, applied, rejected, ops_count, warnings}`；非法/未知 doc_id→404；输出校验失败→500。

- [ ] **Step 1: 写 pydantic 模型**

在 `ppt-editor-service/app/models.py` 末尾追加：
```python
class ApplyPlanRequest(BaseModel):
    doc_id: str
    plan: list[dict[str, Any]]
```
（确认文件顶部已有 `from typing import Any` 与 `from pydantic import BaseModel`；Task 8 已引入，无需重复。）

- [ ] **Step 2: 写失败测试**

`ppt-editor-service/tests/test_api_plan.py`:
```python
import io
from pptx import Presentation
from fastapi.testclient import TestClient
import app.main as main_mod
from app.main import app


def _setup(tmp_path):
    from app.storage import Storage
    main_mod.storage = Storage(str(tmp_path))


def test_apply_plan_fill_repeat_drop(tmp_path, basic_pptx_path):
    _setup(tmp_path)
    client = TestClient(app)
    with open(basic_pptx_path, "rb") as f:
        doc = client.post("/parse", files={"file": ("t.pptx", f, "application/octet-stream")}).json()
    doc_id = doc["doc_id"]

    plan = [
        {"kind": "fill", "slide_id": "s1", "fields": {"s1_sh1": "新封面标题"}},
        {"kind": "repeat", "slide_id": "s2", "items": [
            {"s2_sh1": "要点一"}, {"s2_sh1": "要点二"}, {"s2_sh1": "要点三"}]},
        {"kind": "drop", "slide_id": "s1"},
    ]
    resp = client.post("/apply_plan", json={"doc_id": doc_id, "plan": plan})
    assert resp.status_code == 200
    body = resp.json()
    assert body["rejected"] == []
    assert body["ops_count"] >= 5
    name = body["download_url"].split("/files/")[1]

    out = client.get(f"/files/{name}")
    prs = Presentation(io.BytesIO(out.content))
    titles = [s.shapes[0].text_frame.text for s in prs.slides]
    # 原 s1 已删；剩 原s2 + 3 张副本
    assert len(prs.slides) == 4
    assert "要点一" in titles and "要点三" in titles


def test_apply_plan_unknown_doc(tmp_path):
    _setup(tmp_path)
    client = TestClient(app)
    resp = client.post("/apply_plan", json={"doc_id": "deadbeef", "plan": []})
    assert resp.status_code == 404


def test_apply_plan_malformed_doc(tmp_path):
    _setup(tmp_path)
    client = TestClient(app)
    resp = client.post("/apply_plan", json={"doc_id": "../../etc", "plan": []})
    assert resp.status_code == 404
```

- [ ] **Step 3: 运行确认失败**

```bash
python -m pytest tests/test_api_plan.py -v
```
Expected: FAIL（/apply_plan 未定义 → 404 路由缺失或 422）

- [ ] **Step 4: 写实现**

在 `ppt-editor-service/app/main.py` 的 import 区补充：
```python
from .plan import expand_plan
from .models import ApplyRequest, ApplyPlanRequest
from .parser import parse_presentation
from .storage import Storage, valid_doc_id
```
（若这些已部分 import，合并即可，勿重复 import。）

在 `apply_endpoint` 之后新增端点：
```python
@app.post("/apply_plan")
def apply_plan_endpoint(req: ApplyPlanRequest):
    if not valid_doc_id(req.doc_id) or not storage.exists(req.doc_id):
        raise HTTPException(status_code=404, detail="doc_id 不存在")
    prs = Presentation(storage.source_path(req.doc_id))
    structure = parse_presentation(prs)
    ops, warnings = expand_plan(req.plan, structure)
    applied, rejected = apply_ops(prs, ops)
    out = storage.output_path(req.doc_id)
    prs.save(out)
    try:
        Presentation(out)
    except Exception:
        raise HTTPException(status_code=500, detail="生成的 pptx 校验失败")
    name = os.path.basename(out)
    return {"download_url": f"/files/{name}", "applied": applied,
            "rejected": rejected, "ops_count": len(ops), "warnings": warnings}
```

- [ ] **Step 5: 运行确认通过**

```bash
python -m pytest tests/test_api_plan.py -v
```
Expected: PASS（3 passed）

- [ ] **Step 6: 写演示脚本**

`ppt-editor-service/scripts/demo_plan.py`:
```python
"""手动验证 plan→/apply_plan：
PYTHONPATH=. python scripts/demo_plan.py input.pptx output.pptx
"""
import sys
from pptx import Presentation
from app.parser import parse_presentation
from app.plan import expand_plan
from app.applier import apply_ops


def main():
    src, dst = sys.argv[1], sys.argv[2]
    prs = Presentation(src)
    structure = parse_presentation(prs)
    first_slide = structure["slides"][0]["slide_id"]
    plan = [
        {"kind": "fill", "slide_id": first_slide,
         "fields": {structure["slides"][0]["shapes"][0]["shape_id"]: "PLAN 演示标题"}},
    ]
    ops, warnings = expand_plan(plan, structure)
    applied, rejected = apply_ops(prs, ops)
    prs.save(dst)
    print(f"ops={len(ops)} applied={applied} rejected={rejected} warnings={warnings} -> {dst}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: 手动跑演示脚本**

```bash
cd ppt-editor-service
python - <<'PY'
from pptx import Presentation
p=Presentation(); s=p.slides.add_slide(p.slide_layouts[0]); s.shapes.title.text="原"; p.save("_demo_in.pptx")
PY
PYTHONPATH=. python scripts/demo_plan.py _demo_in.pptx _demo_out.pptx
rm -f _demo_in.pptx _demo_out.pptx
```
Expected: 打印 `ops=1 applied=1 rejected=[] warnings=[] -> _demo_out.pptx`

- [ ] **Step 8: 跑全量 + 提交**

```bash
python -m pytest -v
git add ppt-editor-service/app/models.py ppt-editor-service/app/main.py ppt-editor-service/scripts/demo_plan.py ppt-editor-service/tests/test_api_plan.py
git commit -m "feat(ppt): /apply_plan 端点（plan 展开+回写）+ 演示脚本"
```
Expected: 全部 PASS。

---

### Task 4: Dify 工作流改造（拆两个 LLM + 换 /apply_plan）

**Files:**
- Modify: `ppt-editor-service/dify/ppt-template-llm-edit.yml`

**Interfaces:**
- Consumes: 运行中的服务 `/parse`（含 skeleton）与 `/apply_plan`。
- Produces: 一份可导入的 DSL，节点链 `start → http_parse → code_extract → llm_a → llm_b → code_plan → http_apply_plan → end`。本任务为配置交付，验收靠 YAML 解析校验 + 内嵌代码可执行校验 + 真实 Dify 人工跑通。

**说明**：保留现有 `start`、`http_parse`（/parse）、`end` 的结构与 `app/start/env` 变量；替换中间的「单 LLM + 校验 code」为下述 6 个节点。两个 LLM 节点的 `model`（provider/name/completion_params）**直接复制现有 llm 节点的 model 配置**（保持你环境里的模型可用），仅替换 prompt_template。

- [ ] **Step 1: 备份当前可用 yml**

```bash
cd ppt-editor-service/dify
cp ppt-template-llm-edit.yml ppt-template-llm-edit.单LLM.bak.yml
```

- [ ] **Step 2: 替换 graph.edges 为线性 7 条**

把 `workflow.graph.edges` 整段替换为：
```yaml
    edges:
    - {id: e1, source: start, sourceHandle: source, target: http_parse, targetHandle: target, type: custom, data: {sourceType: start, targetType: http-request, isInIteration: false}}
    - {id: e2, source: http_parse, sourceHandle: source, target: code_extract, targetHandle: target, type: custom, data: {sourceType: http-request, targetType: code, isInIteration: false}}
    - {id: e3, source: code_extract, sourceHandle: source, target: llm_a, targetHandle: target, type: custom, data: {sourceType: code, targetType: llm, isInIteration: false}}
    - {id: e4, source: llm_a, sourceHandle: source, target: llm_b, targetHandle: target, type: custom, data: {sourceType: llm, targetType: llm, isInIteration: false}}
    - {id: e5, source: llm_b, sourceHandle: source, target: code_plan, targetHandle: target, type: custom, data: {sourceType: llm, targetType: code, isInIteration: false}}
    - {id: e6, source: code_plan, sourceHandle: source, target: http_apply_plan, targetHandle: target, type: custom, data: {sourceType: code, targetType: http-request, isInIteration: false}}
    - {id: e7, source: http_apply_plan, sourceHandle: source, target: end, targetHandle: target, type: custom, data: {sourceType: http-request, targetType: end, isInIteration: false}}
```

- [ ] **Step 3: 在 graph.nodes 里保留 start / http_parse，新增/替换中间节点，并改 http_apply_plan 与 end**

**code_extract**（替换原校验 code 节点；从 /parse 响应分出 doc_id 与 skeleton 字符串）：
```yaml
    - id: code_extract
      type: custom
      position: {x: 600, y: 282}
      data:
        type: code
        title: 提取骨架
        code_language: python3
        variables:
        - {variable: parse_body, value_selector: [http_parse, body]}
        code: |
          def main(parse_body: str) -> dict:
              import json
              doc_id = ""
              skeleton = "{}"
              try:
                  pj = json.loads(parse_body)
                  doc_id = pj.get("doc_id", "")
                  skeleton = json.dumps(pj.get("skeleton", {}), ensure_ascii=False)
              except Exception:
                  pass
              return {"doc_id": doc_id, "skeleton": skeleton}
        outputs:
          doc_id: {type: string}
          skeleton: {type: string}
```

**llm_a**（内容创作；model 复制现有 llm 节点）：
```yaml
    - id: llm_a
      type: custom
      position: {x: 860, y: 282}
      data:
        type: llm
        title: 生成内容
        model: { PASTE_FROM_EXISTING_LLM_NODE: true }   # ← 用现有 llm 节点的 model 段替换整个 model:
        context: {enabled: false, variable_selector: []}
        vision: {enabled: false}
        prompt_template:
        - role: system
          text: |
            你是资深PPT文案专家，只负责创作内容，不管排版、不输出任何 shape_id。
            只输出 JSON，包含 deck 数组，不要解释、不要代码块包裹。
            规则：
            1. deck 每项的 use 必须取自给定 skeleton 里出现过的页面 role（如 cover/content/table/generic）。
            2. 可重复页（如 content）用 {"use":"content","repeat":true,"items":[...]}，items 条数按用户需求来，内容要写满、具体、有数据感（每条 2-3 句）。
            3. 固定页用 {"use":"cover","title":"...","subtitle":"..."} 这类字段。
            4. 表格页用 {"use":"table","title":"...","table":{"headers":[...],"rows":[[...]]}}。
            输出示例：
            {"deck":[
              {"use":"cover","title":"2026 产品发布","subtitle":"让服务快人一步"},
              {"use":"content","repeat":true,"items":[
                {"title":"要点一","body":"具体内容……"},
                {"title":"要点二","body":"具体内容……"}
              ]},
              {"use":"table","title":"对比","table":{"headers":["指标","前","后"],"rows":[["响应","30s","3s"]]}}
            ]}
        - role: user
          text: |
            模板骨架（skeleton）：
            {{#code_extract.skeleton#}}

            用户需求：
            {{#start.user_brief#}}

            请只输出 deck 的 JSON。
```

**llm_b**（映射；model 复制现有 llm 节点）：
```yaml
    - id: llm_b
      type: custom
      position: {x: 1120, y: 282}
      data:
        type: llm
        title: 映射到plan
        model: { PASTE_FROM_EXISTING_LLM_NODE: true }   # ← 同上，整段替换
        context: {enabled: false, variable_selector: []}
        vision: {enabled: false}
        prompt_template:
        - role: system
          text: |
            你是映射器，只把"内容大纲"对到模板骨架的真实 shape_id，不改写内容、不创作。
            只输出 JSON，包含 plan 数组，不要解释、不要代码块包裹。
            规则：
            1. plan 每项的 kind 取 fill / repeat / table / drop 之一。
            2. fill: {"kind":"fill","slide_id":"<skeleton里的slide_id>","fields":{"<真实shape_id>":"文本"}}。
            3. repeat: {"kind":"repeat","slide_id":"<可重复页slide_id>","items":[{"<shape_id>":"文本",...}, ...]}，items 条数=内容大纲里该可重复页的 items 条数。
            4. table: {"kind":"table","shape_id":"<table槽的shape_id>","rows":[[...],[...]]}（含表头行）。
            5. drop: {"kind":"drop","slide_id":"<用不到的页>"}。
            6. fields/各item 的 key 必须是 skeleton 中真实存在的 shape_id，严禁编造。
            7. 不要生成临时ID、不要排 dup 顺序——服务端会处理。
            输出示例：
            {"plan":[
              {"kind":"fill","slide_id":"s1","fields":{"s1_sh1":"2026 产品发布","s1_sh2":"让服务快人一步"}},
              {"kind":"repeat","slide_id":"s2","items":[{"s2_sh1":"要点一","s2_sh2":"内容"},{"s2_sh1":"要点二","s2_sh2":"内容"}]},
              {"kind":"table","shape_id":"s3_sh4","rows":[["指标","前","后"],["响应","30s","3s"]]}
            ]}
        - role: user
          text: |
            模板骨架（skeleton）：
            {{#code_extract.skeleton#}}

            内容大纲：
            {{#llm_a.text#}}

            请只输出 plan 的 JSON。
```

**code_plan**（从 llm_b 输出抠出 plan 数组）：
```yaml
    - id: code_plan
      type: custom
      position: {x: 1380, y: 282}
      data:
        type: code
        title: 提取plan
        code_language: python3
        variables:
        - {variable: llm_text, value_selector: [llm_b, text]}
        code: |
          def main(llm_text: str) -> dict:
              import json, re
              plan = []
              m = re.search(r"\{.*\}", llm_text or "", re.S)
              if m:
                  try:
                      plan = json.loads(m.group(0)).get("plan", [])
                  except Exception:
                      plan = []
              return {"plan_json": json.dumps(plan, ensure_ascii=False),
                      "valid": 1 if plan else 0}
        outputs:
          plan_json: {type: string}
          valid: {type: number}
```

**http_apply_plan**（替换原 http_apply；POST /apply_plan）：
```yaml
    - id: http_apply_plan
      type: custom
      position: {x: 1640, y: 282}
      data:
        type: http-request
        title: 回写PPT(plan)
        method: post
        url: '{{#env.SVC#}}/apply_plan'
        authorization: {type: no-auth, config: null}
        headers: 'Content-Type:application/json'
        params: ''
        body:
          type: json
          data: '{"doc_id": "{{#code_extract.doc_id#}}", "plan": {{#code_plan.plan_json#}}}'
        timeout: {max_connect_timeout: 0, max_read_timeout: 0, max_write_timeout: 0}
```

**end**（输出指向 http_apply_plan）：
```yaml
    - id: end
      type: custom
      position: {x: 1900, y: 282}
      data:
        type: end
        title: 结束
        outputs:
        - {variable: apply_result, value_selector: [http_apply_plan, body]}
```

删除原有的 `llm`（单 LLM）、`code`（旧校验）、`http_apply` 三个节点。

- [ ] **Step 4: 校验 YAML 可解析 + 节点齐全 + 内嵌 code 可执行**

```bash
cd ppt-editor-service
python - <<'PY'
import yaml, json, re
d = yaml.safe_load(open("dify/ppt-template-llm-edit.yml", encoding="utf-8"))
nodes = {n["id"] for n in d["workflow"]["graph"]["nodes"]}
need = {"start","http_parse","code_extract","llm_a","llm_b","code_plan","http_apply_plan","end"}
assert need <= nodes, f"缺节点: {need - nodes}"
assert {"llm","code","http_apply"} & nodes == set(), "旧节点未删除"
g = {n["id"]: n for n in d["workflow"]["graph"]["nodes"]}
# code_extract 可跑
ns={}; exec(g["code_extract"]["data"]["code"], ns)
out = ns["main"](json.dumps({"doc_id":"deadbeef","skeleton":{"slides":[]}}))
assert out["doc_id"]=="deadbeef" and json.loads(out["skeleton"])=={"slides":[]}
# code_plan 可跑
ns2={}; exec(g["code_plan"]["data"]["code"], ns2)
out2 = ns2["main"]('x {"plan":[{"kind":"drop","slide_id":"s9"}]} y')
assert json.loads(out2["plan_json"])[0]["kind"]=="drop" and out2["valid"]==1
# apply_plan body 拼接是合法 JSON
body = '{"doc_id": "%s", "plan": %s}' % (out["doc_id"], out2["plan_json"])
assert json.loads(body)["plan"][0]["slide_id"]=="s9"
print("DSL 校验通过：节点齐全、旧节点已删、两段 code 可执行、apply_plan body 合法")
PY
```
Expected: 打印「DSL 校验通过…」。若失败按提示修正（最常见：忘删旧节点、`model:` 占位没替换成真实 model 段导致 Dify 导入报错）。

- [ ] **Step 5: 提交**

```bash
git add ppt-editor-service/dify/ppt-template-llm-edit.yml ppt-editor-service/dify/ppt-template-llm-edit.单LLM.bak.yml
git commit -m "feat(ppt): Dify 工作流改造为 内容LLM→映射LLM→/apply_plan"
```

- [ ] **Step 6: 真实 Dify 人工验收（部署后）**

把更新后的 yml 导入 Dify（`model:` 两处替换为真实模型段后），SVC 指向运行中的服务，上传真实模板 + 需求跑完整链路。
Expected（肉眼）：下载的 pptx **内容明显变厚、页数随 items 数自适应、样式不走样**；结束节点 `apply_result` 里 `rejected` 基本为空、`ops_count` 与内容量匹配。

---

## Self-Review

**Spec 覆盖核对：**
- §2 流水线/改动范围 → Task 1（skeleton+/parse）、Task 3（/apply_plan）、Task 4（Dify）。✓
- §3 skeleton 结构 + role 规则 → Task 1。✓
- §3 LLM-A/LLM-B 契约 → Task 4 的两个 LLM prompt（与 spec 示例一致）。✓
- §4 展开器 4 规则 + 临时 ID/短 ID + 表格自适应 → Task 2。✓
- §4 /apply_plan 端点 + ops_count + warnings → Task 3。✓
- §4 边界（空 items/畸形 shape_id/未知 kind）→ Task 2 测试覆盖。✓
- §5 错误处理（LLM 非法 JSON 兜底、doc 校验、输出校验、局部拒绝）→ Task 4 code 节点（try-parse）、Task 3（404/500 + rejected 透传）。✓
- §6 测试四层 → Task 1（skeleton）、Task 2（展开器）、Task 3（/apply_plan 集成）、Task 4 Step6（人工验收）。✓
- §7 实现顺序（先服务后 Dify）→ Task 1-3 服务、Task 4 Dify。✓
- §8 范围外 → 未纳入。✓

**Placeholder 扫描：** 无 TBD/TODO。Task 4 的 `model: { PASTE_FROM_EXISTING_LLM_NODE: true }` 是**显式的人工替换占位**（带校验 Step 强制其被真实 model 段替换），非遗漏——因为正确的 model 段依赖用户环境的具体模型，计划无法臆造；已在 Step3 注释与 Step4 校验提示中明确。

**类型一致性：** `expand_plan(plan, structure) -> (ops, warnings)` 在 Task 2 定义、Task 3 一致使用；`build_skeleton(parsed) -> dict` 在 Task 1 定义、Task 4 的 code_extract 读取其 `skeleton` 字段结构一致；临时 ID 格式 `{slide_id}__r{i}` 与短 ID 推导在 Task 2 与 spec 一致；`/apply_plan` 返回字段（download_url/applied/rejected/ops_count/warnings）Task 3 定义、Task 4 end 节点读取 body 一致。✓
