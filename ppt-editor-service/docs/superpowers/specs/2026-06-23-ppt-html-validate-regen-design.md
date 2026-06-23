# PPT HTML 渲染校验 + 坏页重生成 设计

日期：2026-06-23
状态：已确认，待实现计划

## 1. 背景与目标

Dify 工作流 `ppt-editor-service/dify/测试.yml` 中的 `PPT生成(HTML)` 节点
（id `17809017899256`，单次批量生成全部页面，每页一个
`<section id="slide-N" class="slide layout-X">`）产出的 PPT 经常出现两类排版问题：

1. **内容溢出**：单页内容超出 960×540 页面边界。
2. **内容重叠**：页内文本元素相互叠压。

目标：在该节点之后增加一个**渲染校验**环节，自动找出有问题的页面，
并对这些页面进行**一次性批量重生成**修复。

## 2. 关键决策（已与用户确认）

| 维度 | 决策 |
|------|------|
| 检测机制 | 真实渲染检测：FastAPI 服务新增 Playwright 无头浏览器端点，Dify 经 HTTP 调用 |
| 重生成方式 | 单次批量改写：一个 LLM 节点接收完整 HTML + 坏页反馈，只改坏页、原样返回其余页，输出完整 HTML（不使用 Iteration/Loop，避开导入失败） |
| 重试轮数 | 只修 1 轮 |
| 应用范围 | 只改主分支（`17809017899256`）；文件里另外 2 个 `PPT生成(HTML)` 分支本期不动 |
| 服务部署 | 校验端点加到现有 `ppt-editor-service` FastAPI 服务 |

## 3. 架构

### 3.1 Dify 图改动

当前主分支边：

- `17809017899256`（PPT生成）→ `178090178992511`（构建历史JSON，code）
- `17809017899256`（PPT生成）→ `17809017899252`（PPT产物类型(HTML)）

改为插入校验/改写链：

```
PPT生成(HTML) 17809017899256
   └→ [新] HTTP校验节点 (http-request)
          POST {VALIDATOR_URL}/validate   body = { "html": {{#17809017899256.text#}} }
        └→ [新] 代码节点·解析校验结果 (code, python3)
              输入: HTTP 节点 .body  →  输出: bad_count(number), feedback(string)
            └→ [新] IF/ELSE 条件分支 (if-else)
                 ├ bad_count > 0 → [新] LLM改写节点 (llm) ─┐
                 └ else ──────────────────────────────────┤
                                       [新] 变量聚合器 (variable-aggregator) final_html
                                            ├→ 178090178992511 构建历史JSON
                                            └→ 17809017899252 PPT产物类型(HTML)
```

要删除的边：

- `17809017899256` → `178090178992511`
- `17809017899256` → `17809017899252`

要新增的边：

- `17809017899256` → HTTP校验节点
- HTTP校验 → 解析code → IF/ELSE
- IF/ELSE(true) → LLM改写 → 变量聚合器
- IF/ELSE(else) → 变量聚合器
- 变量聚合器 → `178090178992511`
- 变量聚合器 → `17809017899252`

下游变量引用改写（共 3 处，把 `{{#17809017899256.text#}}` / selector `[17809017899256, text]`
改成聚合器输出 `[<aggId>, output]`）：

1. `178090178992511`（构建历史JSON）的 `v0` value_selector
2. `生成结尾总结 (3)`（id `17809017899253` 区域，line ~8441）prompt 文本
3. `PPT结果回复 (3)`（id `17809017899254`，line ~8479）answer 文本

> 说明：`if-else` 与 `variable-aggregator` 是 Dify 原生稳定节点，不同于触发过导入失败的
> `iteration` 节点，导入风险低。清洁的 PPT 走 else 分支，跳过改写，既省一次 LLM 调用，
> 也避免把好页改坏。

### 3.2 `/validate` 端点（FastAPI + Playwright）

- 路由：`POST /validate`
- 入参：`{ "html": "<完整 PPT HTML 字符串>" }`
- 处理：
  1. 启动/复用无头 Chromium，`set_content(html)`，视口 960×540。
  2. 注入 JS，对每个 `section.slide` 测量：
     - **溢出**：任一后代元素 `getBoundingClientRect()` 的 `bottom`/`right`
       超出所属 section 边界 + 容差（默认 `OVERFLOW_TOL=2px`）；或内容容器
       `.content` 的 `scrollHeight > clientHeight + 容差`。
     - **重叠**：收集页内"文本叶子元素"（有非空直接文本、无块级子元素的元素），
       两两求包围盒相交，**排除祖先-后代关系**；相交面积 / 较小元素面积 >
       阈值（默认 `OVERLAP_RATIO=0.25`）即判重叠。
  3. 页号来自 `section` 的 `id="slide-N"`（取 N）；若无则用 DOM 顺序序号兜底。
- 返回：
  ```json
  {
    "bad_pages": [
      {"page": 3, "type": "overflow", "detail": "下溢出约 80px"},
      {"page": 5, "type": "overlap",  "detail": "标题与正文重叠 ~40%"}
    ]
  }
  ```
- 阈值（`OVERFLOW_TOL`、`OVERLAP_RATIO`、视口尺寸）作为模块常量/环境变量，便于调参。
- 错误处理：渲染异常返回 HTTP 500 + `{error}`；Dify 侧解析节点在拿不到
  `bad_pages` 时按"无坏页"放行（fail-open，避免阻断正常出图）。

### 3.3 LLM 改写节点

- 类型：`llm`，复用现有生成所用模型（`minimax-m3` / `wxj/bifrost/bifrost`）。
- system：沿用现有「排版硬约束 · 防止文字重叠与超出页面」全文，并追加：
  > 下面给出整份 PPT HTML 与"问题页清单"。**只重写问题页清单中点名的
  > `<section>`**，其余 section 必须原样逐字保留。输出**完整 HTML**，
  > 仅 HTML，无解释、无 markdown 代码块标记。
- user：注入 `完整HTML = {{#17809017899256.text#}}` 与
  `问题页清单 = {{#解析code.feedback#}}`。
- 输出 `.text` = 修正后的完整 HTML。

### 3.4 变量聚合器

- 类型：`variable-aggregator`，输出变量 `final_html`（output）。
- 两路输入：`[LLM改写.text]` 与 `[17809017899256.text]`（else 路）。
- 下游统一引用 `final_html`。

## 4. 涉及文件

- `ppt-editor-service/app/main.py` —— 新增 `POST /validate` 路由。
- `ppt-editor-service/app/validate.py`（新建）—— 渲染检测逻辑（Playwright + 注入 JS）。
- `ppt-editor-service/requirements.txt` —— 增加 `playwright`。
- 部署/README —— 增加 `playwright install chromium` 步骤说明。
- `ppt-editor-service/tests/test_validate.py`（新建）—— 用已知溢出/重叠/清洁样例验证。
- `ppt-editor-service/dify/测试.yml` —— 主分支插入 4 个新节点、改边、改 3 处引用。

## 5. 风险与缓解

1. **VALIDATOR_URL 待定**：Dify 需经 HTTP 访问到服务。实现接线时由用户提供实际地址
   （如 `http://<主机>:8000`），spec 内用占位符。
2. **整份 HTML 回吐截断**：页数多时单次批量改写可能超 token 被截断。缓解：只 1 轮、
   提示强调"完整输出 + 未点名页逐字保留"；若实际 PPT 常 >15 页，后续再评估退回
   "代码拆页只改坏页"方案（本期不做）。
3. **服务镜像变重**：Playwright + Chromium 约 +400MB。接受（用户已确认加到现有服务）。
4. **YAML 导入失败**：23k 行大文件手改易坏。缓解：改动后做 YAML 解析校验 +
   尽量小步、只用 Dify 原生稳定节点类型。

## 6. 非目标（本期不做）

- 另外 2 个 `PPT生成(HTML)` 分支。
- 多轮循环修复（>1 轮）。
- 代码拆页 / 服务端直接重生成。
- 视觉美观度评分（仅做溢出/重叠两类硬问题）。
