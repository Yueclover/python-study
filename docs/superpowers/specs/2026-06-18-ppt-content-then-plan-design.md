# PPT 内容先行 + 计划映射（B2）设计文档

- 日期：2026-06-18
- 状态：设计已确认，待写实现计划
- 关联：在 [2026-06-18-ppt-template-llm-edit-design.md](2026-06-18-ppt-template-llm-edit-design.md) 的服务之上演进

## 1. 背景与目标

现状工作流用**一次 LLM** 直接「用户需求 → 编辑指令 ops JSON」，导致最终 PPT **内容太少且不完整**。

根因：单次调用同时干两件难事——①创作内容（需发散、需篇幅）②机械映射到 shape_id / 算 dup_slide / 维护 JSON 与顺序。两者抢同一次输出预算，模型还要分心维护 ID 和格式，内容自然做薄。

**目标**：把「创作」与「映射」「展开」三者分离，让内容更厚实、映射更可靠。

### 已确认决策

| 维度 | 决策 |
|------|------|
| 内容与模板关系 | C：LLM 看「精简骨架 skeleton」，既知约束又能决定增删页 |
| 内容结构化程度 | B：强结构化、对齐骨架槽位 |
| LLM 次数 | B2：两次 LLM（LLM-A 纯创作 + LLM-B 映射） |
| plan→ops 展开位置 | 服务端新增 `/apply_plan`（TDD），不放 Dify 代码节点 |

### 不变量（沿用上一份设计，本次不改）

5 条指令（set_text/set_cell/set_table_size/dup_slide/del_slide）、确定性 ID（`s{n}` / `s{n}_sh{m}` / 临时 `tmp::sh`）、`apply_ops` 局部拒绝、回写从原始 `source.pptx` 出发另存输出——**全部复用，一行不改**。

## 2. 新流水线与改动范围

```
[开始] file + user_brief
   │
[HTTP /parse]  → slides + 新增 skeleton + doc_id
   │
[代码 提取]    json 解析，分出 doc_id / skeleton
   │
[LLM-A 内容]   user_brief + skeleton → 内容大纲 JSON   ← 自由创作，不碰 shape_id
   │
[LLM-B 映射]   skeleton + 内容大纲 → plan(对到 shape_id/slide_id)  ← 机械映射
   │
[代码 提取]    抠出 plan JSON + 补 doc_id
   │
[HTTP /apply_plan]  服务端 plan→ops 展开 + 回写 → download_url
   │
[结束]
```

### 改动两块

**① 服务（新增，TDD）**
| 改动 | 说明 |
|------|------|
| `/parse` 响应新增 `skeleton` | 服务端从 slides 提炼的精简骨架（每页角色 + 槽位 shape_id/角色/类型），给两个 LLM 的干净视图 |
| 新增 `/apply_plan` 端点 | 收 `{doc_id, plan}`，服务端展开成 ops 再复用 `apply_ops` |
| 新增 `app/plan.py` 展开器 | `expand_plan(plan, structure) -> ops`，纯函数可单测，承载全部机械活 |

**② Dify 工作流（重排）**
- 原 1 个 LLM 节点 → 拆 LLM-A（内容）+ LLM-B（映射）
- 代码节点从「校验 ops」改为「提取字段转发」
- `/apply` 调用换 `/apply_plan`
- 体现在更新 `ppt-editor-service/dify/ppt-template-llm-edit.yml`

## 3. skeleton + 两个 LLM 契约

### skeleton（`/parse` 新增返回，服务端提炼）

```json
{
  "slides": [
    { "slide_id": "s1", "role": "cover",
      "slots": [
        {"shape_id":"s1_sh1","role":"title","type":"text","sample":"在此输入标题"},
        {"shape_id":"s1_sh2","role":"subtitle","type":"text","sample":"副标题"}
      ]},
    { "slide_id": "s2", "role": "content",
      "slots": [
        {"shape_id":"s2_sh1","role":"title","type":"text","sample":"要点标题"},
        {"shape_id":"s2_sh2","role":"body","type":"text","sample":"要点正文"}
      ]},
    { "slide_id": "s3", "role": "table",
      "slots": [
        {"shape_id":"s3_sh1","role":"title","type":"text"},
        {"shape_id":"s3_sh4","role":"table","type":"table","rows":3,"cols":4}
      ]}
  ]
}
```

**role 规则（纯机械）**：槽位 role —— `ph_type=title/ctrTitle→title`、`subtitle→subtitle`、`body/obj→body`、`type=table→table`、`picture/chart→media`、其余 `other`。页 role —— 有 table 槽→`table`；首页含 title+subtitle→`cover`；只含 title+body→`content`；其余→`generic`。

### LLM-A：内容创作

**输入** `user_brief` + `skeleton`；**输出** 内容大纲（按逻辑页组织，决定数量，不碰 shape_id）：

```json
{
  "deck": [
    { "use": "cover", "title": "2026 智能客服产品发布", "subtitle": "让服务快人一步" },
    { "use": "content", "repeat": true, "items": [
        { "title": "7×24 全天候", "body": "再也不漏单……（写满，2-3句）" },
        { "title": "意图识别 98%", "body": "……" }
    ]},
    { "use": "table", "title": "效果对比", "table": {
        "headers": ["指标","改造前","改造后"],
        "rows": [["响应时长","30s","3s"]]
    }}
  ]
}
```

**System 要点**：你是 PPT 文案专家，只产内容不管排版；`use` 取自 skeleton 的 role；可重复页按需求给 N 条 items（内容写满、具体、有数据感）；不要输出 shape_id。

### LLM-B：映射

**输入** `skeleton` + LLM-A 内容大纲；**输出** plan（对到真实 shape_id/slide_id）：

```json
{
  "plan": [
    {"kind":"fill","slide_id":"s1","fields":{"s1_sh1":"2026 智能客服产品发布","s1_sh2":"让服务快人一步"}},
    {"kind":"repeat","slide_id":"s2","items":[
        {"s2_sh1":"7×24 全天候","s2_sh2":"再也不漏单……"},
        {"s2_sh1":"意图识别 98%","s2_sh2":"……"}
    ]},
    {"kind":"table","shape_id":"s3_sh4","rows":[["指标","改造前","改造后"],["响应时长","30s","3s"]]},
    {"kind":"drop","slide_id":"s_unused"}
  ]
}
```

**System 要点**：只做映射不改内容；fields/各 item 的 key 必须是 skeleton 里真实存在的 shape_id；repeat 的 items 条数 = LLM-A 给的条数；用不到的页用 drop；不要算临时 ID、不要排 dup 顺序（服务端做）。

### 契约关键决策

| 决策 | 理由 |
|------|------|
| LLM-A 用 `use`（角色名）不用 slide_id | 创作不关心具体 ID → 更专注内容 |
| LLM-B 只在 skeleton 里选 shape_id | 选择题而非填空题 → 杜绝编造 ID |
| repeat 用 items 列表而非 count | 数量隐含在内容里，LLM-B 不用单独算数 |
| LLM-B 不碰临时 ID / 顺序 | 最易错的机械活全归服务端展开器 |

## 4. 服务端 `/apply_plan` 展开器

### `app/plan.py`：`expand_plan(plan, structure) -> list[op]`

把 4 种 plan 项确定性展开成已有 5 条 ops。

**① fill**
```
{"kind":"fill","slide_id":"s1","fields":{"s1_sh1":"标题","s1_sh2":"副标题"}}
→ [ set_text(s1_sh1,"标题"), set_text(s1_sh2,"副标题") ]
```

**② repeat**（核心：自动临时 ID + 顺序）
```
{"kind":"repeat","slide_id":"s2","items":[ {"s2_sh1":"A1","s2_sh2":"A2"}, {"s2_sh1":"B1","s2_sh2":"B2"} ]}
→ [ dup_slide(s2, count=2, as=["s2__r1","s2__r2"]),
    set_text("s2__r1::sh1","A1"), set_text("s2__r1::sh2","A2"),
    set_text("s2__r2::sh1","B1"), set_text("s2__r2::sh2","B2") ]
```
- 临时页 ID 由展开器生成：`{slide_id}__r{i}`（唯一）。
- 形状短 ID 从 fields 的 key 推导：`s2_sh1 → sh1`（取最后一段 `_` 之后）。
- dup_slide 必排在所有填充指令之前（展开器保证）。

**③ table**（尺寸自适应 + 逐格填）
```
{"kind":"table","shape_id":"s3_sh4","rows":[["指标","前","后"],["响应","30s","3s"]]}
→ [ set_table_size(s3_sh4,2,3)（仅当与当前尺寸不同）,
    set_cell(s3_sh4,0,0,"指标"), ..., set_cell(s3_sh4,1,2,"3s") ]
```
- 当前行列数从 `structure`（`parse_presentation` 结果）查；一致则省略 set_table_size。

**④ drop**
```
{"kind":"drop","slide_id":"s4"} → [ del_slide(s4) ]
```

### `/apply_plan` 端点

```
POST /apply_plan
请求：{ "doc_id": "...", "plan": [...] }
内部：
  1. 取 source.pptx
  2. structure = parse_presentation(prs)     # 表格当前尺寸等
  3. ops = expand_plan(plan, structure)
  4. applied, rejected = apply_ops(prs, ops)  # 复用，不改
  5. 另存 -out.pptx + 重开校验
响应：{ "download_url", "applied", "rejected", "ops_count" }
```
- 新增 `ops_count`（展开出多少条 ops），便于排查「内容多但只生成几条」。
- `rejected` 仍逐条透传；展开器只造 ops，合法性由 applier 校验。

### 展开器边界决策

| 情况 | 处理 |
|------|------|
| repeat 的 items 为空 | 跳过（该页保持原样），不 dup 不删 |
| fields 的 shape_id 无 `_` | 用原值当短 ID 兜底，最终由 applier reject |
| table 的 rows 不规整 | 以第一行列数为准，缺格不填 |
| 未知 kind | 跳过 + 记 warning 进响应 |

**总原则**：展开器不抛异常、不中断；展不了的交给 applier 逐条 reject 兜底，与「局部拒绝不整体失败」一致。

## 5. 错误处理

| 出错环节 | 处理策略 |
|---------|---------|
| LLM-A 输出非法 JSON | 提取代码节点 try-parse，失败→友好报错结束 |
| LLM-A 内容为空/过短 | 代码节点最小校验（deck 为空→报错） |
| LLM-B 输出非法 JSON / plan 为空 | try-parse 兜底；空 plan 不调 /apply_plan |
| LLM-B 编造 shape_id | 展开后 applier 逐条 reject → rejected[] |
| 展开器遇畸形 plan 项 | 不抛异常：跳过 + warning |
| /apply_plan 回写后文件异常 | 复用：重开校验失败 → 500 |

总原则不变：能局部拒绝就别整体失败，坏数据尽量在靠前代码节点拦掉。

## 6. 测试策略

**1. skeleton 提炼（TDD）**：用 `basic_pptx`/`table_pptx` fixture 断言页/槽位 role 正确、shape_id 与 slides 一致。

**2. plan.py 展开器（TDD，重点）**
| 层级 | 测什么 |
|------|--------|
| fill | fields → set_text 序列 |
| repeat | items=N → dup_slide(count=N) + 正确 `__r{i}::sh{m}` 临时 ID + dup 在填充前 |
| table | 尺寸不同→先 set_table_size 再 set_cell；相同→省略 |
| drop | → del_slide |
| 边界 | 空 items 跳过、畸形 shape_id 兜底、未知 kind 跳过+warning |

**3. /apply_plan 端点（集成）**：黄金用例「cover 填 + content 重复 5 次 + table 填 + drop」→ 调端点 → 下载 → 重解析断言页数/副本内容/表格数据。

**4. Dify 工作流（人工验收）**：真实模板 + 需求跑完整链路，肉眼看内容是否变厚、页数随内容自适应、样式没走样。

## 7. 实现顺序（先服务后 Dify）

```
1. 服务: /parse 加 skeleton          ← TDD
2. 服务: plan.py 展开器              ← TDD，最核心
3. 服务: /apply_plan 端点 + 集成测试  ← TDD
4. 本地脚本: 手写 plan → /apply_plan 验证机械链路
5. Dify: 更新 yml（拆 LLM-A/B + 改代码节点 + 换 /apply_plan）
6. 真实模板端到端验收
```

先把服务端机械正确性测透，再接 Dify 的两个 LLM——把「机械对不对」与「内容好不好」彻底分开。

## 8. 不在本次范围

- 内容长度/字号自适应（避免文字撑爆排版）——留后续
- 图片/配色调整、媒体页复制——仍沿用 v1 限制
- 长 PPT 分批
