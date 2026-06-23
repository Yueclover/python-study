# PPT HTML 渲染校验 + 坏页重生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Dify 主分支 `PPT生成(HTML)` 节点后增加渲染校验，自动找出内容溢出/重叠的页面，并用一次性批量改写修复。

**Architecture:** FastAPI 服务新增 `POST /validate` 端点，用 Playwright 无头 Chromium 在 960×540 真实渲染每个 `<section class="slide">`，纯 Python 函数 `analyze_pages` 套用阈值判定溢出/重叠并返回坏页清单。Dify 主分支插入 6 个原生稳定节点（code→http-request→code→if-else→llm→variable-aggregator），坏页走 LLM 单次批量改写、清洁页走 else，二者经聚合器汇合后供下游使用。

**Tech Stack:** Python 3 / FastAPI / Playwright (sync API + Chromium) / pytest / Dify workflow YAML。

## Global Constraints

- Python 依赖只增不改：`requirements.txt` 追加 `playwright`（不写死小版本，跟随其余依赖 `*` 风格用 `playwright` 即可）。
- 渲染视口固定 **960×540**（与生成 prompt 的页面尺寸一致）。
- 默认阈值：溢出容差 `OVERFLOW_TOL=2.0`px；重叠面积比 `OVERLAP_RATIO=0.25`（相交面积 / 两元素较小面积）。三者及视口写成模块常量，便于调参。
- Dify 改动**只动主分支**（`PPT生成(HTML)` id `17809017899256`），另外 2 个 `PPT生成(HTML)` 分支本期不动。
- Dify 只用原生稳定节点（`code` / `http-request` / `if-else` / `variable-aggregator`），**禁止** `iteration` / `loop`（曾导致导入失败）。
- 校验失败时 **fail-open**：拿不到合法 `bad_pages` 一律按"无坏页"放行，绝不阻断正常出图。
- `VALIDATOR_URL` 为占位符 `http://VALIDATOR_HOST:8000`，接线时由用户替换为 Dify 实际可达地址。
- 文件编码 UTF-8；中文原样保留。

---

## File Structure

- `app/validate.py`（新建）—— 渲染校验逻辑：`MEASURE_JS` 注入脚本常量、纯函数 `analyze_pages`、Playwright 包装 `render_and_measure`、组合入口 `validate_html`。
- `app/main.py`（修改）—— 新增 `POST /validate` 路由，薄封装调用 `validate_html`。
- `requirements.txt`（修改）—— 追加 `playwright`。
- `README.md`（修改）—— 增加 `playwright install chromium` 安装步骤。
- `tests/test_validate.py`（新建）—— `analyze_pages` 纯函数单测 + 一个浏览器集成测试（无 Chromium 时跳过）。
- `dify/测试.yml`（修改）—— 主分支插入 6 个新节点、改 2 条边、加 8 条边、改 3 处下游引用。

---

## Task 1: 渲染校验纯逻辑 `analyze_pages`

**Files:**
- Create: `app/validate.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Produces:
  - `analyze_pages(pages: list[dict], overflow_tol: float = 2.0, overlap_ratio: float = 0.25) -> list[dict]`
    - 入参 `pages`：每个元素形如
      `{"page": int, "overflow_right": float, "overflow_bottom": float, "leaves": [{"x":f,"y":f,"w":f,"h":f,"text":str}, ...]}`
    - 返回坏页清单：`[{"page": int, "type": "overflow"|"overlap", "detail": str}, ...]`
  - 模块常量 `VIEWPORT = (960, 540)`、`OVERFLOW_TOL = 2.0`、`OVERLAP_RATIO = 0.25`

- [ ] **Step 1: 写失败测试**

`tests/test_validate.py`：

```python
from app.validate import analyze_pages


def test_clean_page_has_no_issue():
    pages = [{
        "page": 1, "overflow_right": 0.0, "overflow_bottom": 0.0,
        "leaves": [
            {"x": 0, "y": 0, "w": 100, "h": 20, "text": "A"},
            {"x": 0, "y": 40, "w": 100, "h": 20, "text": "B"},
        ],
    }]
    assert analyze_pages(pages) == []


def test_bottom_overflow_flagged():
    pages = [{"page": 3, "overflow_right": 0.0, "overflow_bottom": 80.0, "leaves": []}]
    bad = analyze_pages(pages)
    assert len(bad) == 1
    assert bad[0]["page"] == 3
    assert bad[0]["type"] == "overflow"
    assert "下" in bad[0]["detail"] and "80" in bad[0]["detail"]


def test_small_overflow_within_tolerance_ignored():
    pages = [{"page": 2, "overflow_right": 1.5, "overflow_bottom": 0.0, "leaves": []}]
    assert analyze_pages(pages) == []


def test_overlapping_leaves_flagged():
    pages = [{
        "page": 5, "overflow_right": 0.0, "overflow_bottom": 0.0,
        "leaves": [
            {"x": 0, "y": 0, "w": 100, "h": 100, "text": "标题"},
            {"x": 0, "y": 50, "w": 100, "h": 100, "text": "正文"},  # 50% 纵向重叠
        ],
    }]
    bad = analyze_pages(pages)
    assert any(b["type"] == "overlap" and b["page"] == 5 for b in bad)


def test_adjacent_leaves_not_flagged():
    pages = [{
        "page": 6, "overflow_right": 0.0, "overflow_bottom": 0.0,
        "leaves": [
            {"x": 0, "y": 0, "w": 100, "h": 50, "text": "上"},
            {"x": 0, "y": 50, "w": 100, "h": 50, "text": "下"},  # 仅相邻不相交
        ],
    }]
    assert analyze_pages(pages) == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd ppt-editor-service && python -m pytest tests/test_validate.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'app.validate'`

- [ ] **Step 3: 写最小实现（仅纯逻辑部分）**

`app/validate.py`：

```python
"""PPT HTML 渲染校验：检测单页内容溢出与文本重叠。"""

VIEWPORT = (960, 540)
OVERFLOW_TOL = 2.0      # px：超出页面边界的容差
OVERLAP_RATIO = 0.25    # 相交面积 / 两元素较小面积，超过即判重叠


def _overlap_ratio(a: dict, b: dict) -> float:
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    inter_w = max(0.0, min(ax2, bx2) - max(a["x"], b["x"]))
    inter_h = max(0.0, min(ay2, by2) - max(a["y"], b["y"]))
    inter = inter_w * inter_h
    if inter <= 0:
        return 0.0
    smaller = min(a["w"] * a["h"], b["w"] * b["h"])
    return inter / smaller if smaller > 0 else 0.0


def _max_overlap(leaves: list[dict]):
    """返回 (ratio, textA, textB)；无重叠返回 None。"""
    best = None
    for i in range(len(leaves)):
        for j in range(i + 1, len(leaves)):
            r = _overlap_ratio(leaves[i], leaves[j])
            if best is None or r > best[0]:
                best = (r, leaves[i].get("text", ""), leaves[j].get("text", ""))
    return best


def analyze_pages(pages: list[dict], overflow_tol: float = OVERFLOW_TOL,
                  overlap_ratio: float = OVERLAP_RATIO) -> list[dict]:
    bad = []
    for p in pages:
        right = float(p.get("overflow_right", 0) or 0)
        bottom = float(p.get("overflow_bottom", 0) or 0)
        of = max(right, bottom)
        if of > overflow_tol:
            label = "下" if bottom >= right else "右"
            bad.append({"page": p["page"], "type": "overflow",
                        "detail": f"{label}溢出约{round(of)}px"})
        best = _max_overlap(p.get("leaves", []) or [])
        if best is not None and best[0] > overlap_ratio:
            ratio, ta, tb = best
            bad.append({"page": p["page"], "type": "overlap",
                        "detail": f'文本重叠~{round(ratio * 100)}% ("{ta}" / "{tb}")'})
    return bad
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd ppt-editor-service && python -m pytest tests/test_validate.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: 提交**

```bash
git add ppt-editor-service/app/validate.py ppt-editor-service/tests/test_validate.py
git commit -m "feat(ppt): 渲染校验纯逻辑 analyze_pages（溢出/重叠判定）"
```

---

## Task 2: Playwright 渲染包装 + `/validate` 端点

**Files:**
- Modify: `app/validate.py`（追加 `MEASURE_JS`、`render_and_measure`、`validate_html`）
- Modify: `app/main.py:1-20`（导入与路由）
- Modify: `requirements.txt`
- Modify: `README.md`
- Test: `tests/test_validate.py`（追加集成测试）

**Interfaces:**
- Consumes: `analyze_pages`（Task 1）
- Produces:
  - `render_and_measure(html: str) -> list[dict]` —— 用 Playwright 渲染并返回 Task 1 入参格式的 `pages`
  - `validate_html(html: str) -> dict` —— 返回 `{"bad_pages": [...]}`，渲染异常时返回 `{"bad_pages": [], "error": str}`（fail-open）
  - `POST /validate` 入参 `{"html": str}` → `{"bad_pages": [...]}`

- [ ] **Step 1: 写失败的集成测试（无 Chromium 自动跳过）**

`tests/test_validate.py` 追加：

```python
import importlib.util
import pytest
from fastapi.testclient import TestClient
from app.main import app

_HAS_PW = importlib.util.find_spec("playwright") is not None
client = TestClient(app)


def _chromium_ok() -> bool:
    if not _HAS_PW:
        return False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark_browser = pytest.mark.skipif(
    not _chromium_ok(), reason="Playwright/Chromium 不可用")

_OVERFLOW_HTML = """
<section id="slide-1" class="slide" style="width:960px;height:540px;overflow:hidden;position:relative;">
  <div style="position:absolute;top:900px;">超出页面底部的内容</div>
</section>
"""

_CLEAN_HTML = """
<section id="slide-1" class="slide" style="width:960px;height:540px;overflow:hidden;position:relative;">
  <div style="position:absolute;top:20px;">正常内容</div>
</section>
"""


@pytestmark_browser
def test_validate_detects_overflow():
    resp = client.post("/validate", json={"html": _OVERFLOW_HTML})
    assert resp.status_code == 200
    pages = resp.json()["bad_pages"]
    assert any(p["page"] == 1 and p["type"] == "overflow" for p in pages)


@pytestmark_browser
def test_validate_clean_page():
    resp = client.post("/validate", json={"html": _CLEAN_HTML})
    assert resp.status_code == 200
    assert resp.json()["bad_pages"] == []


def test_validate_endpoint_failopen_on_garbage():
    # 不依赖浏览器：空 html 渲染后无 section，应返回空坏页
    resp = client.post("/validate", json={"html": ""})
    assert resp.status_code == 200
    assert "bad_pages" in resp.json()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd ppt-editor-service && python -m pytest tests/test_validate.py -v`
Expected: FAIL —— `/validate` 返回 404（路由尚不存在），`test_validate_endpoint_failopen_on_garbage` 失败

- [ ] **Step 3: 追加渲染与端点实现**

在 `app/validate.py` 末尾追加：

```python
# 注入浏览器执行：逐 section 测量溢出量与文本叶子元素几何
MEASURE_JS = r"""
() => {
  const secs = Array.from(document.querySelectorAll('section.slide'));
  return secs.map((sec, i) => {
    const sr = sec.getBoundingClientRect();
    let page = i + 1;
    const m = (sec.id || '').match(/slide-(\d+)/);
    if (m) page = parseInt(m[1], 10);
    let overRight = 0, overBottom = 0;
    const leaves = [];
    sec.querySelectorAll('*').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width <= 0 && r.height <= 0) return;
      overRight = Math.max(overRight, r.right - sr.right);
      overBottom = Math.max(overBottom, r.bottom - sr.bottom);
      const txt = (el.textContent || '').trim();
      if (el.children.length === 0 && txt.length > 0 && r.width > 0 && r.height > 0) {
        leaves.push({x: r.left, y: r.top, w: r.width, h: r.height, text: txt.slice(0, 20)});
      }
    });
    return {page: page, overflow_right: overRight, overflow_bottom: overBottom, leaves: leaves};
  });
}
"""


def render_and_measure(html: str) -> list[dict]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]})
            page.set_content(html or "", wait_until="networkidle")
            return page.evaluate(MEASURE_JS)
        finally:
            browser.close()


def validate_html(html: str) -> dict:
    try:
        pages = render_and_measure(html)
    except Exception as exc:  # fail-open：渲染异常不阻断出图
        return {"bad_pages": [], "error": str(exc)}
    return {"bad_pages": analyze_pages(pages)}
```

在 `app/main.py` 修改导入并加路由。导入区追加：

```python
from .validate import validate_html
```

在 `/files/{name}` 路由之前追加：

```python
@app.post("/validate")
def validate_endpoint(req: dict):
    return validate_html(req.get("html", ""))
```

- [ ] **Step 4: 追加依赖与 README 说明**

`requirements.txt` 末尾追加一行：

```
playwright
```

`README.md` 的 `## 运行` 代码块改为：

```bash
pip install -r requirements.txt
playwright install chromium   # 首次需安装无头浏览器（约 +400MB）
PPT_STORAGE=./storage uvicorn app.main:app --host 0.0.0.0 --port 8000
```

并在 `## 接口` 列表追加一行：

```
- POST /validate  ({html}) -> {bad_pages:[{page,type,detail}]}  渲染校验溢出/重叠
```

- [ ] **Step 5: 安装浏览器并运行测试**

Run:
```bash
cd ppt-editor-service && pip install playwright && playwright install chromium && python -m pytest tests/test_validate.py -v
```
Expected: PASS（含浏览器集成测试；若该环境无法启动 Chromium，集成测试 SKIP，其余 PASS）

- [ ] **Step 6: 提交**

```bash
git add ppt-editor-service/app/validate.py ppt-editor-service/app/main.py ppt-editor-service/requirements.txt ppt-editor-service/README.md ppt-editor-service/tests/test_validate.py
git commit -m "feat(ppt): 新增 /validate 渲染校验端点（Playwright 无头 Chromium）"
```

---

## Task 3: Dify 主分支接入校验/改写链

**Files:**
- Modify: `dify/测试.yml`

**说明（节点 id 与引用，供本任务内部一致引用）：**
- 新增节点：`vld_body`(code) → `vld_http`(http-request) → `vld_parse`(code) → `vld_if`(if-else) →〔true〕`vld_llm`(llm) → `vld_agg`(variable-aggregator)；`vld_if`〔false〕直连 `vld_agg`。
- 原节点：`17809017899256`=PPT生成(HTML)；`178090178992511`=构建历史JSON；`17809017899252`=PPT产物类型(HTML)；`17809017899253`=生成结尾总结(3)；`17809017899254`=PPT结果回复(3)。
- `vld_agg` 输出引用为 `{{#vld_agg.output#}}`，selector `[vld_agg, output]`。

- [ ] **Step 1: 备份并确认当前 YAML 合法**

Run:
```bash
cd ppt-editor-service && cp dify/测试.yml dify/测试.yml.bak && python -c "import yaml,sys; yaml.safe_load(open('dify/测试.yml',encoding='utf-8')); print('OK baseline')"
```
Expected: 打印 `OK baseline`

- [ ] **Step 2: 在 `nodes:` 列表中插入 6 个新节点**

在节点 `17809017899256` 的节点块（以 `id: '17809017899256'` 结尾、`width: 242` 那段）之后、紧接的 `- data:` 之前，插入下列 6 个节点块（保持每块以 `    - data:` 起始、缩进与文件一致）：

```yaml
    - data:
        code: "import json\ndef main(html: str) -> dict:\n    return {\"body\": json.dumps({\"html\": html or \"\"}, ensure_ascii=False)}\n"
        code_language: python3
        desc: 构造 /validate 请求体
        isInIteration: false
        isInLoop: false
        outputs:
          body:
            children: null
            type: string
        selected: false
        title: 构造校验请求体
        type: code
        variables:
        - value_selector:
          - '17809017899256'
          - text
          value_type: string
          variable: html
      height: 52
      id: vld_body
      position:
        x: 4646
        y: 2120
      positionAbsolute:
        x: 4646
        y: 2120
      selected: false
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 242
    - data:
        authorization:
          config: null
          type: no-auth
        body:
          data:
          - id: key-value-vld
            key: ''
            type: text
            value: '{{#vld_body.body#}}'
          type: json
        desc: 调用渲染校验端点
        headers: 'Content-Type:application/json'
        isInIteration: false
        isInLoop: false
        method: post
        params: ''
        retry_config:
          max_retries: 2
          retry_enabled: true
          retry_interval: 1500
        selected: false
        ssl_verify: true
        timeout:
          connect: 30
          max_connect_timeout: 300
          max_read_timeout: 600
          max_write_timeout: 600
          read: 300
          write: 300
        title: HTTP校验
        type: http-request
        url: http://VALIDATOR_HOST:8000/validate
        variables: []
      height: 137
      id: vld_http
      position:
        x: 4908
        y: 2120
      positionAbsolute:
        x: 4908
        y: 2120
      selected: false
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 242
    - data:
        code: "import json\ndef main(body: str) -> dict:\n    try:\n        data = json.loads(body) if (body or '').strip() else {}\n    except Exception:\n        return {\"has_bad\": \"no\", \"feedback\": \"\", \"bad_count\": 0}\n    pages = data.get(\"bad_pages\") or []\n    if not isinstance(pages, list) or not pages:\n        return {\"has_bad\": \"no\", \"feedback\": \"\", \"bad_count\": 0}\n    lines = []\n    for it in pages:\n        try:\n            lines.append(f\"- 第{it.get('page')}页: {it.get('detail') or it.get('type')}\")\n        except Exception:\n            pass\n    return {\"has_bad\": \"yes\", \"feedback\": \"\\n\".join(lines), \"bad_count\": len(pages)}\n"
        code_language: python3
        desc: 解析校验结果（fail-open）
        isInIteration: false
        isInLoop: false
        outputs:
          has_bad:
            children: null
            type: string
          feedback:
            children: null
            type: string
          bad_count:
            children: null
            type: number
        selected: false
        title: 解析校验结果
        type: code
        variables:
        - value_selector:
          - vld_http
          - body
          value_type: string
          variable: body
      height: 52
      id: vld_parse
      position:
        x: 5170
        y: 2120
      positionAbsolute:
        x: 5170
        y: 2120
      selected: false
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 242
    - data:
        cases:
        - case_id: 'true'
          conditions:
          - comparison_operator: is
            id: vld-cond-1
            value: 'yes'
            varType: string
            variable_selector:
            - vld_parse
            - has_bad
          id: 'true'
          logical_operator: and
        desc: 有坏页则改写
        isInIteration: false
        isInLoop: false
        selected: false
        title: 是否有坏页
        type: if-else
      height: 126
      id: vld_if
      position:
        x: 5432
        y: 2120
      positionAbsolute:
        x: 5432
        y: 2120
      selected: false
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 242
    - data:
        context:
          enabled: false
          variable_selector: []
        desc: 仅重写坏页，输出完整 HTML
        isInIteration: false
        isInLoop: false
        model:
          completion_params:
            temperature: 0.7
            thinking: false
          mode: chat
          name: minimax-m3
          provider: wxj/bifrost/bifrost
        prompt_template:
        - id: vld_llm_sys
          role: system
          text: "你是PPT排版修复引擎。下面给出整份PPT的HTML与“问题页清单”。\n- 仅重写问题页清单中点名的 <section>，其余 section 必须原样逐字保留。\n- 页面大小 960*540，禁止溢出与文字重叠；内容过多时必须精简/截断，禁止靠缩小字号硬塞。\n- .slide 用 flex 列布局，主体区 flex:1 1 auto; min-height:0; overflow:hidden；禁止用 position:absolute 叠放正文。\n- 输出完整 HTML，仅 HTML，无解释、无 markdown 代码块标记。"
        - id: vld_llm_user
          role: user
          text: "## 问题页清单\n{{#vld_parse.feedback#}}\n\n## 完整PPT HTML\n{{#17809017899256.text#}}"
        selected: false
        title: 坏页改写
        type: llm
        vision:
          enabled: false
      height: 116
      id: vld_llm
      position:
        x: 5694
        y: 2040
      positionAbsolute:
        x: 5694
        y: 2040
      selected: false
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 242
    - data:
        desc: 汇合改写结果与原始HTML
        isInIteration: false
        isInLoop: false
        output_type: string
        selected: false
        title: 最终HTML聚合
        type: variable-aggregator
        variables:
        - - vld_llm
          - text
        - - '17809017899256'
          - text
      height: 134
      id: vld_agg
      position:
        x: 5956
        y: 2120
      positionAbsolute:
        x: 5956
        y: 2120
      selected: false
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 242
```

- [ ] **Step 3: 校验 YAML 合法 + 新节点已就位**

Run:
```bash
cd ppt-editor-service && python -c "import yaml; d=yaml.safe_load(open('dify/测试.yml',encoding='utf-8')); ids=[n['id'] for n in d['workflow']['graph']['nodes']]; assert all(x in ids for x in ['vld_body','vld_http','vld_parse','vld_if','vld_llm','vld_agg']), 'missing node'; print('nodes OK')"
```
Expected: 打印 `nodes OK`（若顶层结构非 `workflow.graph.nodes`，改用 `grep -c \"id: vld_\" dify/测试.yml` 应为 6）

- [ ] **Step 4: 改边——删 2 条旧边、加 8 条新边**

在 `edges:` 列表中删除以下两条边块（整块删除，定位见行号 `1004` 与 `1064` 附近，`source: '17809017899256'`）：
- `id: 17809017899256-source-178090178992511-target`
- `id: 17809017899256-source-17809017899252-target`

然后在 `edges:` 列表任意位置追加下列 8 条边块（与现有边块同缩进 `    - data:`）：

```yaml
    - data:
        isInLoop: false
        sourceType: llm
        targetType: code
      id: 17809017899256-source-vld_body-target
      source: '17809017899256'
      sourceHandle: source
      target: vld_body
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInLoop: false
        sourceType: code
        targetType: http-request
      id: vld_body-source-vld_http-target
      source: vld_body
      sourceHandle: source
      target: vld_http
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInLoop: false
        sourceType: http-request
        targetType: code
      id: vld_http-source-vld_parse-target
      source: vld_http
      sourceHandle: source
      target: vld_parse
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInLoop: false
        sourceType: code
        targetType: if-else
      id: vld_parse-source-vld_if-target
      source: vld_parse
      sourceHandle: source
      target: vld_if
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInLoop: false
        sourceType: if-else
        targetType: llm
      id: vld_if-true-vld_llm-target
      source: vld_if
      sourceHandle: 'true'
      target: vld_llm
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInLoop: false
        sourceType: llm
        targetType: variable-aggregator
      id: vld_llm-source-vld_agg-target
      source: vld_llm
      sourceHandle: source
      target: vld_agg
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInLoop: false
        sourceType: if-else
        targetType: variable-aggregator
      id: vld_if-false-vld_agg-target
      source: vld_if
      sourceHandle: 'false'
      target: vld_agg
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInLoop: false
        sourceType: variable-aggregator
        targetType: code
      id: vld_agg-source-178090178992511-target
      source: vld_agg
      sourceHandle: source
      target: '178090178992511'
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInLoop: false
        sourceType: variable-aggregator
        targetType: code
      id: vld_agg-source-17809017899252-target
      source: vld_agg
      sourceHandle: source
      target: '17809017899252'
      targetHandle: target
      type: custom
      zIndex: 0
```

- [ ] **Step 5: 改 3 处下游引用，指向聚合器输出**

5a. `构建历史JSON`（`178090178992511`）的 `v0` value_selector：把
```yaml
        - value_selector:
          - '17809017899256'
          - text
          value_type: string
          variable: v0
```
改为
```yaml
        - value_selector:
          - vld_agg
          - output
          value_type: string
          variable: v0
```

5b. `生成结尾总结 (3)`（line ~8441，prompt text 内）：把该 LLM 文本里的
`{{#17809017899256.text#}}` 改为 `{{#vld_agg.output#}}`。

5c. `PPT结果回复 (3)`（line ~8479，answer text 内）：把
`{{#17809017899256.text#}}` 改为 `{{#vld_agg.output#}}`。

> 注意：`坏页改写`(`vld_llm`) 与 `构造校验请求体`(`vld_body`) 内引用的
> `{{#17809017899256.text#}}` / `[17809017899256, text]` **保持不变**（它们要的是原始 HTML）。
> 校验：改完后 `{{#17809017899256.text#}}` 在文件中应只剩 1 处（vld_llm 的 user prompt），
> `[17809017899256, text]` selector 应只剩 2 处（vld_body、vld_agg）。

- [ ] **Step 6: 全量校验 YAML + 引用计数 + 无悬空边**

Run:
```bash
cd ppt-editor-service && python -c "
import yaml
d = yaml.safe_load(open('dify/测试.yml', encoding='utf-8'))
g = d['workflow']['graph']
ids = {n['id'] for n in g['nodes']}
for e in g['edges']:
    assert e['source'] in ids, 'dangling source '+e['source']
    assert e['target'] in ids, 'dangling target '+e['target']
print('graph OK, nodes=', len(g['nodes']), 'edges=', len(g['edges']))
"
grep -c "{{#17809017899256.text#}}" dify/测试.yml
```
Expected: 打印 `graph OK ...`；`grep -c` 结果为 `1`

- [ ] **Step 7: 提交并清理备份**

```bash
cd ppt-editor-service && rm dify/测试.yml.bak
git add dify/测试.yml
git commit -m "feat(ppt): Dify 主分支接入渲染校验+坏页改写链"
```

- [ ] **Step 8: 人工导入验证（用户执行）**

把 `dify/测试.yml` 导入自托管 Dify，确认导入不报错、主分支节点连线如设计；把 `vld_http` 节点 URL 的 `VALIDATOR_HOST` 改为 Dify 实际可达的服务地址，跑一次生成验证坏页被检出并改写。

---

## Self-Review

**Spec coverage：**
- §3.1 Dify 图改动（插链/删 2 边/加 8 边/改 3 引用）→ Task 3 Step 2/4/5 全覆盖。
- §3.2 `/validate`（渲染+溢出+重叠+阈值+fail-open）→ Task 1（判定/阈值）+ Task 2（渲染/端点/fail-open）。
- §3.3 LLM 改写（只改坏页、复用硬约束、完整输出）→ Task 3 `vld_llm` 节点 prompt。
- §3.4 变量聚合器 → Task 3 `vld_agg` 节点。
- §4 涉及文件（main/validate/requirements/README/tests/yml）→ 各 Task Files 全覆盖。
- §5 风险：截断（1 轮 + 完整输出提示，已在 vld_llm prompt）、fail-open（vld_parse + validate_html）、镜像变重（README 说明）。

**Placeholder scan：** 无 TBD/TODO；`VALIDATOR_HOST` 是 Global Constraints 显式声明的占位符，Task 3 Step 8 指明替换时机，非计划缺口。

**Type consistency：** `analyze_pages` 入参键 `overflow_right/overflow_bottom/leaves/page` 与 `MEASURE_JS` 返回键一致；`validate_html` 返回 `{"bad_pages":[...]}` 与 `vld_parse` 读取的 `data.get("bad_pages")` 一致；`vld_parse` 输出 `has_bad`(string) 与 `vld_if` 条件 `is "yes"` 一致；`vld_agg` 输出 `output` 与下游 `{{#vld_agg.output#}}` / `[vld_agg, output]` 一致。
