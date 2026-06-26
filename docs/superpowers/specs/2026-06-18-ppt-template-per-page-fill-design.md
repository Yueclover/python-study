# PPT 模板逐页填充改造设计

日期：2026-06-18
状态：已确认，待实现

## 背景与问题

现有 Dify 工作流 `ppt-editor-service/dify/ppt-template-llm-edit.yml`
链路为：`/parse → 提取骨架 → 内容LLM → 映射LLM → 提取plan → /apply_plan`。

存在两个根因明确的问题：

### 问题 1：无法替换模板里所有文字区域

根因在 `app/skeleton.py` 的 `_slot_role`：它只依据 placeholder 类型
（`ph_type`）判断槽位角色，非占位符的普通文本框一律落入 `role="other"`。
真实模板里绝大多数可见文字是普通文本框（`is_placeholder=False`），
因此被标成"杂项"。

下游内容 LLM 只为 cover/content/table/generic 这些角色产出
title/subtitle/body 字段，映射 LLM 只把"已创作的内容"映射到 shape_id，
导致 `other` 槽（=模板里大部分文字）永远拿不到新内容。

本质：内容模型是"按角色创作"而非"按真实文字槽逐个填充"。

### 问题 2：无法识别页面类型（封面/目录/章节/结尾）

根因在 `app/skeleton.py` 的 `_page_role`：
- 词汇表只有 `table / cover / content / generic`，没有 toc / section / ending；
- 判断信号只有 placeholder 组合，模板若无占位符则整本判成 generic。

并且 `app/parser.py` 已抓到的 `layout_name`（版式名，最强信号）在
`build_skeleton` 中被丢弃。

## 目标

1. 覆盖率：模板里每一个可编辑文字槽都能被填上新内容。
2. 页面识别：可靠区分 cover / toc / section / content / table / ending / generic。
3. 页数随内容增减：正文等可重复页按用户需求扩展为多页。
4. 后端 `/apply_plan`、`plan.py`、`applier.py` 不改动，复用现有 plan 协议。

## 架构

```
/parse  →  code提取  →  大纲LLM  →  code(join)  →  Dify Iteration(逐页填)  →  code组装plan  →  /apply_plan  →  end
          (skeleton)   (定页数)    (贴slots)       (每页1次LLM,填满槽位)       (fill/repeat/drop)
```

设计原则：**大纲负责"说什么 + 几页"（连贯性 + 页数），逐页 loop 负责
"把每页每个槽填满"（覆盖率）。** 二者结合，而非二选一。

为什么不用纯"直接根据骨架填"：骨架页数 = 模板页数，固定。"正文要几页"
的决策骨架里没有，必须有大纲步骤先算出来。

## 组件设计

### 1. 增强版 skeleton（改 `app/skeleton.py`）

#### 1.1 页面分类 `_page_role`

入参从"仅 slot_roles"扩展为可见 `layout_name`、页面文本、页序、槽位组合。
按优先级命中即停，词汇表 `cover / toc / section / content / table / ending / generic`：

| 优先级 | 信号 | 判定 |
|---|---|---|
| 1 | 有 table 槽 | `table` |
| 2 | `layout_name`（最强） | 含 封面/标题幻灯片 → `cover`；目录/contents/agenda → `toc`；节标题/章/过渡/section/divider/part → `section`；结束/谢谢/致谢/封底/thank/end → `ending` |
| 3 | 页面正文关键词 | 目录/CONTENTS/AGENDA → `toc`；谢谢/感谢/THANK/THANKS → `ending`；第x章/PART/Chapter → `section` |
| 4 | 页序 | index==0 且有标题 → `cover`；最后一页且仍未定 → `ending` |
| 5 | 槽位组合（兜底） | title+subtitle → `cover`；title+body → `content` |
| 6 | 其余 | `generic` |

匹配时英文转小写、中文原样比较。关键词集合以常量列表维护，便于扩充。

#### 1.2 槽位增强 `_slot`

每个槽新增字段：
- `current_text`：当前**全文**（移除现有 `sample = text[:30]` 的 30 字截断）。
- `editable`：`type == "text"` 即 `true`。

普通文本框 role 仍为 `other`，但 `editable=true` —— 逐页填充正是对着这些
槽填，这是覆盖率的来源。页码/装饰性固定文字 v1 不做专门检测，靠逐页 LLM
提示词"保持原样不变"处理（YAGNI，后续可加位置/字号启发式）。

#### 1.3 `build_skeleton`

每页输出补上 `layout_name`（来自 `parser.py` 的解析结果），供分类与大纲使用：

```json
{"slides":[
  {"slide_id":"s1","role":"cover","layout_name":"标题幻灯片",
   "slots":[
     {"shape_id":"s1_sh1","role":"title","type":"text","current_text":"公司名","editable":true},
     {"shape_id":"s1_sh2","role":"other","type":"text","current_text":"2026.06","editable":true}
   ]}
]}
```

### 2. 大纲 LLM（Dify 节点，替换原"生成内容"节点）

- 输入：`user_brief` + 各页 `{slide_id, role}` 清单（可附一行槽位摘要）。
- 约束：**只决定每页内容与正文页数量，不改变页面顺序**（顺序由模板定）。
- 输出：

```json
{"outline":[
  {"use_slide_id":"s1","role":"cover","brief":"主标题X 副标题Y"},
  {"use_slide_id":"s2","role":"toc","brief":"目录：列出4个章节标题"},
  {"use_slide_id":"s5","role":"content","brief":"正文要点1：..."},
  {"use_slide_id":"s5","role":"content","brief":"正文要点2：..."}
]}
```

正文要 N 个要点，就产出 N 项都指向正文页 `slide_id` —— 这一步决定页数。

### 3. code「join」（新增节点，Iteration 之前）

为每个 outline 项贴上其 `use_slide_id` 对应的 `slots`，产出 `tasks[]`：

```json
{"tasks":[{"slide_id":"s5","role":"content","brief":"...","slots":[{...}]}]}
```

让迭代 LLM 直接看到该页真实槽位，无需再查 skeleton。

### 4. Dify Iteration（遍历 tasks，每项 1 次 LLM）

每次迭代输入一个 task（含 slots + brief），LLM 把该页**每个 editable 槽**填满，
输出：

```json
{"slide_id":"s5","fields":{"s5_sh1":"...","s5_sh2":"..."}}
```

约束：fields 的 key 必须取自本 task 的 slots（只见一页 shape_id，天然不串页）；
页码/装饰性固定文字保持原 `current_text` 不变。连贯性由大纲的 brief 保证。

### 5. code「组装 plan」（替换原"提取plan"节点）

收集 Iteration 输出数组，按 `slide_id` 分组（保持模板原顺序）：
- 某 slide_id 被引用 **1 次** → `fill`：`{"kind":"fill","slide_id":...,"fields":{...}}`
- 被引用 **N>1 次** → `repeat`：`{"kind":"repeat","slide_id":...,"items":[fields1, fields2, ...]}`（items 顺序 = 大纲顺序）
- 模板里**未被任何产出页引用**的 slide_id → `drop`：`{"kind":"drop","slide_id":...}`

输出 `plan_json` 喂 `/apply_plan`。**无需"可重复页"标志位**——"被引用几次"
天然决定 fill 还是 repeat，通用且简单。

### 6. `/apply_plan`（后端，不改动）

继续吃现有 plan 协议（fill/repeat/table/drop）。`plan.py` 的 `expand_plan`
已能把 repeat 展开为 dup_slide + set_text，table、drop 同理。风险最小。

## 数据流示例

模板：s1 封面、s2 目录、s5 正文页、s9 结尾。用户要 3 个正文要点。

1. skeleton：4 页，roles = cover/toc/content/ending。
2. 大纲：outline = [cover×1, toc×1, content(s5)×3, ending×1]。
3. join：tasks = 6 项，各带 slots。
4. Iteration：6 次 LLM，各产出 fields。
5. 组装：s1→fill, s2→fill, s5→repeat(items=3), s9→fill；无 drop。
6. /apply_plan：dup s5 三次分别填，其余 fill。输出含 3 页正文的新 pptx。

## 测试策略

- `app/skeleton.py`：
  - `_page_role` 各分类分支单测（layout_name / 关键词 / 页序 / 槽位组合 / 兜底）。
  - `_slot` 输出含 `current_text`（全文）与 `editable`。
  - `build_skeleton` 输出含 `layout_name`。
  - 用 `tests/test_skeleton.py` 现有夹具扩展。
- 组装 plan 的分组逻辑（1次→fill / N次→repeat / 未引用→drop）：
  若放在 Dify code 节点，补一份可独立运行的纯函数 + 单测（建议抽到
  `app/` 下便于测试，Dify 节点再调用或复制）。
- 端到端：`scripts/demo_plan.py` 思路扩展一个 demo，验证多正文页 round-trip。

## 改动落点

- `app/skeleton.py`：分类升级 + 槽位增强 + 输出 layout_name。
- `ppt-editor-service/dify/ppt-template-llm-edit.yml`：重构为
  outline → join → Iteration → assemble。
- 后端 `/apply_plan` / `plan.py` / `applier.py`：不改。

## 非目标（YAGNI）

- 页码/页脚/装饰文字的自动检测（v1 靠提示词保持原样）。
- 模板页面顺序的重排（顺序由模板决定）。
- 图片/图表内容替换（仅文字与表格）。
- LLM 逐页分类兜底（v1 先用确定性启发式，覆盖不了再议）。
