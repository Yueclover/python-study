# PPT 模板逐页填充改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 PPT 模板编辑工作流能可靠识别每页类型、填满每个文字槽，并按内容增减页数。

**Architecture:** 后端 `app/skeleton.py` 升级页面分类与槽位信息；新增 `app/assemble.py` 把"逐页填充结果"组装成 plan（fill/repeat/drop）；Dify 工作流重构为 大纲LLM → join → Iteration（逐页填）→ assemble → /apply_plan。后端 `/apply_plan`、`plan.py`、`applier.py` 不改。

**Tech Stack:** Python 3 + python-pptx + pytest；Dify 工作流 YAML。

## Global Constraints

- 后端 `app/plan.py`、`app/applier.py`、`/apply_plan` 端点**不得修改**——复用现有 plan 协议（fill/repeat/table/drop）。
- 页面角色词汇表固定为：`cover / toc / section / content / table / ending / generic`。
- 分类用确定性启发式（layout_name + 关键词 + 页序 + 槽位组合），不引入额外 LLM 调用。
- 现有测试 `tests/test_skeleton.py`、`tests/test_plan.py` 必须保持通过。
- 所有命令在 `ppt-editor-service/` 目录下运行（pytest 的 rootdir）。
- v1 边界：表格页的表格栅格内容**不在逐页 loop 中重建**（其文字槽照常填充，表格保留模板原样）；页码/装饰固定文字靠提示词保持不变。

---

## 文件结构

- 修改 `app/skeleton.py`：`_slot`（加 current_text/editable）、`_page_role`（重写分类）、`build_skeleton`（输出 layout_name、传新参数）。
- 新建 `app/assemble.py`：`assemble_plan(page_outputs, skeleton)` 纯函数。
- 新建 `tests/test_assemble.py`：assemble 单测。
- 扩展 `tests/test_skeleton.py`：分类与槽位单测。
- 修改 `ppt-editor-service/dify/ppt-template-llm-edit.yml`：重构节点。

---

## Task 1: 槽位增强（current_text 全文 + editable）

**Files:**
- Modify: `app/skeleton.py`（函数 `_slot`，约 27-39 行）
- Test: `tests/test_skeleton.py`

**Interfaces:**
- Consumes: 解析后的 shape dict（含 `shape_id` / `type` / `text` / `table`）。
- Produces: 每个 slot dict 含字段 `current_text`（str，全文）与 `editable`（bool，`type=="text"` 为真）；保留 `shape_id` / `role` / `type`，表格槽仍含 `rows` / `cols`。**移除旧的 `sample` 字段。**

- [ ] **Step 1: 写失败测试**

在 `tests/test_skeleton.py` 末尾追加：

```python
def test_slot_has_full_current_text_and_editable(basic_pptx_path):
    parsed = parse_presentation(Presentation(basic_pptx_path))
    sk = build_skeleton(parsed)
    title_slot = next(s for s in sk["slides"][0]["slots"] if s["role"] == "title")
    assert title_slot["current_text"] == "原标题"     # 全文，不截断
    assert title_slot["editable"] is True
    assert "sample" not in title_slot


def test_table_slot_not_editable(table_pptx_path):
    parsed = parse_presentation(Presentation(table_pptx_path))
    sk = build_skeleton(parsed)
    tslot = next(s for s in sk["slides"][0]["slots"] if s["role"] == "table")
    assert tslot["editable"] is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_skeleton.py::test_slot_has_full_current_text_and_editable tests/test_skeleton.py::test_table_slot_not_editable -v`
Expected: FAIL（KeyError 'current_text' / 'editable'）

- [ ] **Step 3: 改 `_slot` 实现**

把 `app/skeleton.py` 的 `_slot` 替换为：

```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_skeleton.py -v`
Expected: PASS（含原有 `test_skeleton_cover_and_content` / `test_skeleton_table_page`）

- [ ] **Step 5: 提交**

```bash
git add app/skeleton.py tests/test_skeleton.py
git commit -m "feat(ppt): skeleton 槽位输出全文 current_text 与 editable"
```

---

## Task 2: build_skeleton 输出 layout_name

**Files:**
- Modify: `app/skeleton.py`（函数 `build_skeleton`，约 42-51 行）
- Test: `tests/test_skeleton.py`

**Interfaces:**
- Consumes: `parsed["slides"][i]["layout_name"]`（`parser.py` 已提供）。
- Produces: skeleton 每个 slide dict 含字段 `layout_name`（str）。

- [ ] **Step 1: 写失败测试**

在 `tests/test_skeleton.py` 末尾追加：

```python
def test_skeleton_exposes_layout_name(basic_pptx_path):
    parsed = parse_presentation(Presentation(basic_pptx_path))
    sk = build_skeleton(parsed)
    # python-pptx 默认模板：第一页版式名为 "Title Slide"
    assert sk["slides"][0]["layout_name"] == "Title Slide"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_skeleton.py::test_skeleton_exposes_layout_name -v`
Expected: FAIL（KeyError 'layout_name'）

- [ ] **Step 3: 改 `build_skeleton` 实现**

把 `app/skeleton.py` 的 `build_skeleton` 替换为（暂不改分类调用，分类在 Task 3 处理）：

```python
def build_skeleton(parsed):
    slides = []
    for sl in parsed["slides"]:
        slots = [_slot(sh) for sh in sl["shapes"]]
        slides.append({
            "slide_id": sl["slide_id"],
            "role": _page_role([s["role"] for s in slots]),
            "layout_name": sl["layout_name"],
            "slots": slots,
        })
    return {"slides": slides}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_skeleton.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/skeleton.py tests/test_skeleton.py
git commit -m "feat(ppt): skeleton 输出 layout_name"
```

---

## Task 3: 页面分类升级（cover/toc/section/content/table/ending/generic）

**Files:**
- Modify: `app/skeleton.py`（函数 `_page_role` 重写；`build_skeleton` 更新调用；文件顶部加 `import re`）
- Test: `tests/test_skeleton.py`

**Interfaces:**
- Consumes: `slot_roles`（list[str]）、`layout_name`（str）、`page_text`（str，全页文字拼接）、`index`（int，0 基）、`total`（int，总页数）。
- Produces: `_page_role(slot_roles, layout_name, page_text, index, total) -> str`，返回值取自固定词汇表。`build_skeleton` 用 `sl["index"]`、`len(parsed["slides"])`、各 shape 的 `text` 拼接调用它。

- [ ] **Step 1: 写失败测试（纯函数分支 + 集成）**

在 `tests/test_skeleton.py` 顶部 import 处补充：

```python
from app.skeleton import build_skeleton, _page_role
```

在文件末尾追加：

```python
def test_page_role_table_wins():
    assert _page_role(["title", "table"], "Whatever", "", 1, 3) == "table"

def test_page_role_layout_cover():
    assert _page_role(["title"], "Title Slide", "", 1, 3) == "cover"
    assert _page_role(["title"], "封面页", "", 1, 3) == "cover"

def test_page_role_layout_toc():
    assert _page_role(["title", "body"], "目录", "", 1, 3) == "toc"
    assert _page_role(["title"], "Agenda", "", 1, 3) == "toc"

def test_page_role_layout_section():
    assert _page_role(["title"], "Section Header", "", 1, 3) == "section"
    assert _page_role(["title"], "节标题", "", 1, 3) == "section"

def test_page_role_layout_ending():
    assert _page_role(["title"], "结束页", "", 2, 3) == "ending"

def test_page_role_text_keyword_toc():
    assert _page_role(["title", "body"], "Blank", "目录 第一部分 第二部分", 1, 3) == "toc"

def test_page_role_text_keyword_ending():
    assert _page_role(["other"], "Blank", "谢谢观看", 2, 3) == "ending"

def test_page_role_text_keyword_section():
    assert _page_role(["title"], "Blank", "第一章 总览", 1, 4) == "section"

def test_page_role_index0_title_is_cover():
    assert _page_role(["title"], "Blank", "某标题", 0, 3) == "cover"

def test_page_role_last_sparse_is_ending():
    assert _page_role(["other"], "Blank", "再见", 2, 3) == "ending"

def test_page_role_composition_fallbacks():
    assert _page_role(["title", "subtitle"], "Blank", "x", 1, 3) == "cover"
    assert _page_role(["title", "body"], "Blank", "x", 1, 3) == "content"

def test_page_role_generic_default():
    assert _page_role(["other"], "Blank", "一些正文 内容很多 不止一个槽",
                      1, 3) == "generic"
```

并修改原有集成测试中对 content 的断言保持不变（`test_skeleton_cover_and_content` 已断言 s2 == "content"，分类升级后仍须成立）。

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_skeleton.py -v`
Expected: FAIL（`_page_role` 旧签名只接受 1 个参数 → TypeError）

- [ ] **Step 3: 重写 `_page_role` 并更新调用**

在 `app/skeleton.py` 顶部加：

```python
import re
```

把 `_page_role` 替换为：

```python
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
```

把 `build_skeleton` 中调用 `_page_role` 的那行替换为带上下文的调用：

```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_skeleton.py -v`
Expected: PASS（全部，含原有两条集成测试）

- [ ] **Step 5: 提交**

```bash
git add app/skeleton.py tests/test_skeleton.py
git commit -m "feat(ppt): 页面分类升级 cover/toc/section/content/table/ending"
```

---

## Task 4: assemble_plan —— 逐页结果组装为 plan

**Files:**
- Create: `app/assemble.py`
- Test: `tests/test_assemble.py`

**Interfaces:**
- Consumes: `page_outputs`（list，按大纲顺序，每项 `{"slide_id": str, "fields": {shape_id: text}}`）；`skeleton`（dict，`{"slides":[{"slide_id":...}, ...]}`）。
- Produces: `assemble_plan(page_outputs, skeleton) -> list`，按模板顺序返回 plan 项：被引用 1 次→`{"kind":"fill","slide_id","fields"}`；>1 次→`{"kind":"repeat","slide_id","items":[...]}`（items 按出现顺序）；未引用→`{"kind":"drop","slide_id"}`。skeleton 中不存在的 slide_id 忽略。

- [ ] **Step 1: 写失败测试**

新建 `tests/test_assemble.py`：

```python
from app.assemble import assemble_plan


def test_single_use_becomes_fill():
    sk = {"slides": [{"slide_id": "s1"}]}
    out = [{"slide_id": "s1", "fields": {"s1_sh1": "A"}}]
    assert assemble_plan(out, sk) == [
        {"kind": "fill", "slide_id": "s1", "fields": {"s1_sh1": "A"}}]


def test_multiple_use_becomes_repeat_in_order():
    sk = {"slides": [{"slide_id": "s5"}]}
    out = [{"slide_id": "s5", "fields": {"s5_sh1": "A"}},
           {"slide_id": "s5", "fields": {"s5_sh1": "B"}}]
    assert assemble_plan(out, sk) == [
        {"kind": "repeat", "slide_id": "s5",
         "items": [{"s5_sh1": "A"}, {"s5_sh1": "B"}]}]


def test_unreferenced_slide_dropped():
    sk = {"slides": [{"slide_id": "s1"}, {"slide_id": "s2"}]}
    out = [{"slide_id": "s1", "fields": {"s1_sh1": "A"}}]
    plan = assemble_plan(out, sk)
    assert {"kind": "fill", "slide_id": "s1", "fields": {"s1_sh1": "A"}} in plan
    assert {"kind": "drop", "slide_id": "s2"} in plan


def test_output_follows_template_order():
    sk = {"slides": [{"slide_id": "s1"}, {"slide_id": "s2"}, {"slide_id": "s3"}]}
    out = [{"slide_id": "s3", "fields": {"x": "3"}},
           {"slide_id": "s1", "fields": {"x": "1"}}]
    plan = assemble_plan(out, sk)
    assert [p["slide_id"] for p in plan] == ["s1", "s2", "s3"]
    assert plan[1] == {"kind": "drop", "slide_id": "s2"}


def test_unknown_slide_id_ignored():
    sk = {"slides": [{"slide_id": "s1"}]}
    out = [{"slide_id": "s1", "fields": {"x": "1"}},
           {"slide_id": "zzz", "fields": {"y": "2"}}]
    plan = assemble_plan(out, sk)
    assert plan == [{"kind": "fill", "slide_id": "s1", "fields": {"x": "1"}}]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_assemble.py -v`
Expected: FAIL（ModuleNotFoundError: app.assemble）

- [ ] **Step 3: 写实现**

新建 `app/assemble.py`：

```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_assemble.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/assemble.py tests/test_assemble.py
git commit -m "feat(ppt): assemble_plan 逐页结果组装为 plan"
```

---

## Task 5: Dify 工作流重构（outline → join → Iteration → assemble）

**Files:**
- Modify: `ppt-editor-service/dify/ppt-template-llm-edit.yml`

**Interfaces:**
- Consumes: `/parse` 返回的增强 skeleton（含 layout_name / slots.current_text / slots.editable / role）。
- Produces: 发往 `/apply_plan` 的 `{"doc_id", "plan"}`，plan 由 assemble 逻辑产出。

说明：Dify code 节点在独立沙箱运行，无法 import `app.assemble`，因此 join / assemble 逻辑需**内联**到 code 节点；其参考实现与单测在 `app/assemble.py`，两者须保持一致（assemble 内联代码逻辑与 `assemble_plan` 等价）。本任务为配置改造，验证以"YAML 可解析 + 内联 Python 可编译 + 手动导入 Dify 跑通"为准。

- [ ] **Step 1: 改 code_extract 节点，透传完整 skeleton**

将 `code_extract` 节点的 code 改为同时输出 doc_id、skeleton 字符串、以及每页 `{slide_id, role}` 精简清单（供大纲 LLM 用）：

```python
def main(parse_body: str) -> dict:
    import json
    doc_id, skeleton, pages = "", "{}", "[]"
    try:
        pj = json.loads(parse_body)
        doc_id = pj.get("doc_id", "")
        sk = pj.get("skeleton", {})
        skeleton = json.dumps(sk, ensure_ascii=False)
        pages = json.dumps(
            [{"slide_id": s["slide_id"], "role": s["role"]}
             for s in sk.get("slides", [])], ensure_ascii=False)
    except Exception:
        pass
    return {"doc_id": doc_id, "skeleton": skeleton, "pages": pages}
```

并把 `outputs` 增加 `pages: {type: string}`。

- [ ] **Step 2: 替换 llm_a 为"大纲 LLM"**

将 `llm_a`（生成内容）的 system / user 提示词改为输出 outline（决定页数、不改页面顺序）：

system：

```
你是PPT结构规划师。根据用户需求和模板页面清单，规划要产出的每一页。
只输出 JSON，含 outline 数组，不要解释、不要代码块包裹。
规则：
1. outline 每项 = {"use_slide_id":"<模板页slide_id>","role":"<该页role>","brief":"这页要写的内容要点"}。
2. 不要改变页面顺序；正文等可重复页要几页就重复列几项（use_slide_id 相同）。
3. role 取自页面清单里出现过的值（cover/toc/section/content/table/ending/generic）。
4. brief 要具体、可直接据此写文案；正文每项 2-3 句、有数据感。
输出示例：
{"outline":[
  {"use_slide_id":"s1","role":"cover","brief":"主标题:2026产品发布；副标题:让服务快人一步"},
  {"use_slide_id":"s2","role":"toc","brief":"目录4项:背景/方案/数据/计划"},
  {"use_slide_id":"s5","role":"content","brief":"背景:市场规模..."},
  {"use_slide_id":"s5","role":"content","brief":"方案:三步走..."}
]}
```

user：

```
模板页面清单（slide_id 与 role）：
{{#code_extract.pages#}}

用户需求：
{{#start.user_brief#}}

请只输出 outline 的 JSON。
```

- [ ] **Step 3: 新增 code「join」节点（在大纲与 Iteration 之间）**

新增 code 节点 `code_join`，输入 `outline_text`（来自大纲 LLM 文本）与 `skeleton`（来自 code_extract），输出 `tasks`（JSON 字符串，供 Iteration 遍历）：

```python
def main(outline_text: str, skeleton: str) -> dict:
    import json, re
    outline = []
    m = re.search(r"\{.*\}", outline_text or "", re.S)
    if m:
        try:
            outline = json.loads(m.group(0)).get("outline", [])
        except Exception:
            outline = []
    slots_by_slide = {}
    try:
        for s in json.loads(skeleton).get("slides", []):
            slots_by_slide[s["slide_id"]] = [
                sl for sl in s.get("slots", []) if sl.get("editable")]
    except Exception:
        pass
    tasks = []
    for it in outline:
        sid = it.get("use_slide_id")
        if sid not in slots_by_slide:
            continue
        tasks.append({
            "slide_id": sid,
            "role": it.get("role", ""),
            "brief": it.get("brief", ""),
            "slots": slots_by_slide[sid],
        })
    return {"tasks": json.dumps(tasks, ensure_ascii=False),
            "count": len(tasks)}
```

`outputs`: `tasks: {type: string}`, `count: {type: number}`。

- [ ] **Step 4: 新增 Iteration 节点（逐页填）**

新增 Dify Iteration 节点，迭代输入 = `code_join.tasks`（需为数组；若 Dify 要求数组类型，用一个 code 节点把 `tasks` JSON 字符串 `json.loads` 成数组对象输出，或直接让 code_join 输出 `array[object]` 类型）。每次迭代内放一个 LLM 节点：

system：

```
你是PPT文案填充器。把给定页面的每个文本槽填上最终文字。
只输出 JSON：{"slide_id":"<本页slide_id>","fields":{"<shape_id>":"文本",...}}。
不要解释、不要代码块包裹。
规则：
1. fields 的 key 只能用本页 slots 里给的 shape_id，不得编造、不得用别页的。
2. 每个可编辑槽都要给出文本；页码/日期/装饰性固定文字保持其 current_text 原值。
3. 内容依据 brief，贴合该页 role（封面写标题副标题、目录写条目、正文写要点）。
```

user：

```
本页 slide_id：{{#iteration.item.slide_id#}}
本页角色 role：{{#iteration.item.role#}}
本页内容要点 brief：{{#iteration.item.brief#}}
本页文本槽 slots（含 shape_id 与 current_text）：
{{#iteration.item.slots#}}

请只输出该页的 JSON。
```

Iteration 输出收集每次 LLM 的 text 成数组。

- [ ] **Step 5: 替换 code_plan 为「assemble」节点**

将原 `code_plan` 改为消费 Iteration 输出数组（每项是 LLM 文本）与 skeleton，内联 assemble 逻辑输出 plan_json：

```python
def main(iter_outputs: list, skeleton: str) -> dict:
    import json, re
    page_outputs = []
    for t in iter_outputs or []:
        m = re.search(r"\{.*\}", t or "", re.S)
        if not m:
            continue
        try:
            o = json.loads(m.group(0))
        except Exception:
            continue
        if o.get("slide_id") and isinstance(o.get("fields"), dict):
            page_outputs.append({"slide_id": o["slide_id"],
                                 "fields": o["fields"]})
    sk = {}
    try:
        sk = json.loads(skeleton)
    except Exception:
        sk = {}
    # 内联 assemble_plan（与 app/assemble.py 等价）
    by_slide = {}
    for o in page_outputs:
        by_slide.setdefault(o["slide_id"], []).append(o["fields"])
    plan = []
    for sl in sk.get("slides", []):
        sid = sl.get("slide_id")
        occs = by_slide.get(sid, [])
        if not occs:
            plan.append({"kind": "drop", "slide_id": sid})
        elif len(occs) == 1:
            plan.append({"kind": "fill", "slide_id": sid, "fields": occs[0]})
        else:
            plan.append({"kind": "repeat", "slide_id": sid, "items": occs})
    return {"plan_json": json.dumps(plan, ensure_ascii=False),
            "valid": 1 if plan else 0}
```

`outputs`: `plan_json: {type: string}`, `valid: {type: number}`。`http_apply_plan` 的 body 改引用 `{{#code_assemble.plan_json#}}`（节点 id 按实际命名）。

- [ ] **Step 6: 更新 edges 串联新链路**

把 graph.edges 改为：`start → http_parse → code_extract → llm_a(大纲) → code_join → iteration → code_assemble → http_apply_plan → end`。删除/替换原 `llm_b`、`code_plan` 相关 edge 与 node。

- [ ] **Step 7: 结构校验**

Run: `python -c "import yaml; yaml.safe_load(open('dify/ppt-template-llm-edit.yml', encoding='utf-8')); print('yaml ok')"`
Expected: 打印 `yaml ok`，无异常。

逐个 code 节点把其 `code:` 文本贴到本地 `.py` 临时文件用 `python -m py_compile` 校验可编译（或人工核对缩进）。Expected: 无语法错误。

- [ ] **Step 8: 手动验证（导入 Dify 跑通）**

导入工作流到 Dify，用一个含 封面/目录/正文/结尾 的模板 pptx + 一段需求运行，确认：
1. 输出 pptx 每页文字都被替换（覆盖率）；
2. 页面类型识别正确（目录页填成目录、结尾页填成结束语）；
3. 正文页数随 brief 数量增减。
Expected: 三项均满足；`/apply_plan` 返回 download_url，rejected 为空或可解释。

- [ ] **Step 9: 提交**

```bash
git add dify/ppt-template-llm-edit.yml
git commit -m "feat(ppt): Dify 工作流重构为 大纲→join→逐页填→组装"
```

---

## Self-Review 记录

- **Spec 覆盖**：问题1覆盖率→Task1（current_text/editable）+Task5（逐页填提示词"每个可编辑槽都要填"）；问题2分类→Task2/3；页数增减→Task4（assemble fill/repeat/drop）+Task5（大纲重复列项、Iteration）。后端不改→Global Constraints。
- **占位符**：无 TBD/TODO；每步含完整代码与命令。
- **类型一致**：`_page_role` 五参签名在 Task3 定义、build_skeleton 调用一致；`assemble_plan(page_outputs, skeleton)` 在 Task4 定义、Task5 内联等价。
- **已知边界（非缺口）**：表格页栅格内容不在逐页 loop 重建（Global Constraints 已声明，符合 spec 第5节只 fill/repeat/drop）。
```
