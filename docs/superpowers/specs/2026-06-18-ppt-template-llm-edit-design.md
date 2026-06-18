# PPT 模板 LLM 编辑系统 设计文档

- 日期：2026-06-18
- 状态：设计已确认，待写实现计划

## 1. 背景与目标

在 Dify 平台实现：**用户上传 PPT 模板 → LLM 学习模板风格并生成新内容 → 回写成新的 .pptx 供下载**，且后续可在 Dify 流程中对该 PPT 反复编辑。

### 已确认的关键决策

| 维度 | 决策 |
|------|------|
| 输出形态 | 真 .pptx 文件（不经过 HTML 中间层） |
| LLM 改动范围 | 文字 + 表格数据 + 增删整页 |
| 语义识别方式 | LLM 自动识别（模板零准备，靠结构化信号辅助） |
| 后端 | 新建 Python FastAPI 服务（与 python-pptx 同生态） |
| 架构方案 | 方案 1「编辑指令模式」：LLM 只输出带稳定 ID 的操作指令 |

### 为什么不走 HTML

PPT→HTML 有损，HTML→PPT 再有损，多轮编辑必然样式走样。编辑场景要求"可往返"，以 .pptx 为唯一真相源、JSON 为中间层最稳。HTML 在本目标下是多余的。

## 2. 整体架构

```
┌─────────────┐      ┌──────────────────────────────┐
│   用户       │      │   Dify 工作流（编排层）        │
│ 上传 pptx    │─────▶│  HTTP节点 → LLM节点 → HTTP节点 │
│ 下载 pptx    │◀─────│                                │
└─────────────┘      └──────────────┬───────────────┘
                                    │ HTTP 调用
                          ┌─────────▼──────────┐
                          │ PPT 服务 (FastAPI)  │
                          │  python-pptx        │
                          │  ① /parse  解析     │
                          │  ② /apply  回写     │
                          └─────────┬──────────┘
                                    │
                          ┌─────────▼──────────┐
                          │  存储 (本地盘 v1)    │
                          └────────────────────┘
```

### 三组件分工

| 组件 | 职责 | 不负责 |
|------|------|--------|
| PPT 服务 (FastAPI) | 解析 pptx→JSON、按指令回写 pptx、存取文件 | 不调 LLM、不懂语义 |
| Dify 工作流 | 编排：拿 JSON → 喂 LLM → 拿指令 → 回传服务 | 不碰 pptx 二进制 |
| LLM 节点 | 识别语义、生成内容、产出编辑指令清单 | 不直接产 pptx |

**核心设计**：PPT 服务是"纯机械手"，只认 ID 和指令；语义全交给 LLM。两边可独立测试、独立演进。

### 完整数据流

```
1. 用户在 Dify 上传 template.pptx
2. Dify → POST /parse   → { doc_id, slides:[...带ID的JSON] }
3. Dify → LLM 节点       → 输入 JSON + 用户需求 → 输出 编辑指令清单
4. Dify → POST /apply   → 输入 doc_id + 指令 → { download_url, rejected }
5. 用户下载新 pptx
```

`doc_id` 把"解析"和"回写"两次调用串联：服务在 /parse 时把原始 pptx 与分配的 ID 映射落盘，/apply 时按同一份映射精确回写。LLM 全程只接触 JSON 和指令。

## 3. 解析后的 JSON 数据结构

LLM 的"眼睛"。原则：够识别语义 + 够回写定位，不堆无用细节（省 token）。

### 顶层

```json
{
  "doc_id": "a1b2c3",
  "slide_size": { "width": 12192000, "height": 6858000 },
  "slides": [ /* 每页一个对象 */ ]
}
```

### 单页

```json
{
  "slide_id": "s1",
  "index": 0,
  "layout_name": "标题幻灯片",
  "shapes": [ /* 形状列表 */ ]
}
```

### 单个形状

```json
{
  "shape_id": "s1_sh3",
  "type": "text | table | picture | chart | other",
  "name": "Title 1",
  "ph_type": "title | body | null",
  "pos": { "x":838200, "y":365125, "w":10515600, "h":1325563 },
  "text": "在此输入标题",
  "style": { "font": "微软雅黑", "size": 44, "bold": true, "color": "#1F3864", "align": "center" },
  "table": { "rows": 3, "cols": 4, "cells": [ { "r":0,"c":0,"text":"季度" } ] }
}
```

### 设计决策

| 决策 | 理由 |
|------|------|
| ID 用 `页_形状` 复合编码（`s1_sh3`） | 归属一目了然，回写按 ID 直查 |
| 保留 `ph_type` / `name` | 自动识别标题/正文的最强信号，弥补自动识别风险 |
| `pos` 用 EMU 原值 | 回写免换算，LLM 可据坐标判断角色 |
| 图片/图表只给 ID+位置 | LLM 改不了图但需知其存在；省大量 token |
| 样式只抽段落级代表值 | 逐 run 抽样式会让 JSON 爆炸；代表值足够表达风格 |

## 4. 编辑指令 Schema（LLM 的「手」）

LLM 不产 pptx、不改 JSON，只输出指令清单。

### 整体形态

```json
{
  "doc_id": "a1b2c3",
  "ops": [
    { "op": "set_text",  "shape_id": "s1_sh3", "text": "2026 产品发布会" },
    { "op": "set_cell",  "shape_id": "s2_sh5", "r": 1, "c": 2, "text": "85%" },
    { "op": "dup_slide", "slide_id": "s3", "count": 5, "as": ["d1","d2","d3","d4","d5"] },
    { "op": "set_text",  "shape_id": "d1::sh2", "text": "要点一：性能提升 3 倍" },
    { "op": "del_slide", "slide_id": "s4" }
  ]
}
```

### 指令集（v1 仅 5 条）

| 指令 | 参数 | 作用 |
|------|------|------|
| `set_text` | shape_id, text | 改文本框文字（保留原样式） |
| `set_cell` | shape_id, r, c, text | 改表格某单元格 |
| `dup_slide` | slide_id, count, as[] | 复制某页 N 份，返回新页临时 ID |
| `del_slide` | slide_id | 删除某页 |
| `set_table_size` | shape_id, rows, cols | 表格增删行列 |

### 两个关键机制

**① 增删页后引用副本里的形状**：`dup_slide` 用 `as` 给每份副本一个临时页 ID（如 `d1`），副本里的形状用 `临时页ID::原形状短ID`（如 `d1::sh2`）引用。服务应用 `dup_slide` 时建立 `d1 → 真实新 slide` 映射，后续指令按此翻译。好处：一份指令内即可"复制 5 页 + 分别填不同内容"。

**② 指令顺序 = 执行顺序**：服务严格按数组顺序执行，LLM 必须先 `dup_slide` 再填副本。写进 system prompt 强约束。

### 为什么只给 5 条

指令越少 LLM 越不易乱来（不开放改图/配色/坐标 → 模板风格天然保真）；每条都能机械校验（不存在/类型不符/越界直接拒绝）；已覆盖"文字+数据+增删页"需求。图片替换、配色调整留 v2。

## 5. FastAPI 服务接口

服务是纯机械手，只认 ID 和指令。

### POST /parse — 解析

```
请求：multipart/form-data，file = template.pptx
响应：{ "doc_id", "slide_size", "slides": [...] }
```
内部：存原始 pptx → 遍历分配 ID → 落盘 `doc_id → (pptx路径 + ID映射)` → 返回 JSON。

### POST /apply — 回写

```
请求：{ "doc_id", "ops": [...] }
响应：{
  "download_url": "...",
  "applied": 8,
  "rejected": [ { "index":5, "op":"set_text", "reason":"shape_id s9_sh1 不存在" } ]
}
```
内部：取原 pptx → 逐条校验+应用（建临时ID映射）→ 另存 `-out.pptx` → 返回下载链接 + 逐条结果。

### GET /files/{name} — 下载

返回 pptx 二进制（`Content-Disposition: attachment`）。

### 设计决策

| 决策 | 理由 |
|------|------|
| 解析/回写两次调用靠 doc_id 串联 | LLM 只碰 JSON；回写从原始母版出发，零样式损耗 |
| /apply 返回 rejected[] 而非整体失败 | 单条错不影响其余，结果可观测可重试 |
| /apply 另存 -out.pptx 不改原文件 | 原模板可复用，支持同模板多次生成 |
| doc_id 状态落盘 | parse 与 apply 之间隔着 LLM 调用（数十秒），重启不丢 |

### 状态存储（v1 最简）

```
storage/
  a1b2c3/
    source.pptx        # 原始模板
    idmap.json         # ID → (slide索引 + shape索引) 定位映射
    a1b2c3-out.pptx    # 生成结果
```
`idmap.json` 存定位路径而非 python-pptx 对象（对象不可序列化）；/apply 时重新打开 pptx 按路径定位。几十页体量完全可接受。v2 上云换 OSS/S3 + Redis，接口不变。

## 6. Dify 工作流编排 + LLM Prompt

### 节点串联

```
[开始]  输入 file(pptx) + user_brief
[HTTP节点1: 解析]  POST /parse → parse_result(doc_id + slides)
[LLM节点: 生成指令]  输入 slides + user_brief → ops_json
[代码节点: 校验/提取]  确认合法 JSON、补 doc_id → { doc_id, ops }
[HTTP节点2: 回写]  POST /apply → apply_result(download_url + rejected)
[结束]  返回 download_url（有 rejected 则附提示）
```

### LLM Prompt

**System（强约束）：**
```
你是PPT编辑指令生成器。只能输出JSON，包含ops数组。
可用指令仅5种：set_text / set_cell / dup_slide / del_slide / set_table_size。
铁律：
1. shape_id/slide_id 必须来自输入JSON，严禁编造。
2. 复制页填内容时，必须先 dup_slide 再用 as 里的临时ID(如 d1::sh2) 填副本。
3. ops 按数组顺序执行，dup_slide 必须排在引用其副本的指令之前。
4. 不改样式、不改坐标、不动图片。只改文字、表格数据、增删页。
5. 识别语义靠 ph_type / name / 位置 / 字号。
```

**User（运行时拼接）：**
```
模板结构：{{parse_result.slides}}
用户需求：{{user_brief}}
请生成编辑指令。
```

### 提升识别准确率的抓手

| 抓手 | 做法 |
|------|------|
| JSON 自带强信号 | 保留 ph_type/name/pos/size，prompt 明确要求据此判断角色 |
| Few-shot 示例 | system 里塞 1 个完整「slides → ops」例子，提升格式稳定性 |
| JSON 输出强制 | 用 Dify LLM 节点 JSON 输出模式 + prompt 给 schema |

### 工程提醒

- **长 PPT token 问题**：几十页 JSON 可能超上下文。v1 不优化；v2 可按页分批或先让 LLM 选页再细化。
- **校验代码节点不可省**：LLM 偶尔输出非法 JSON，代码节点做解析兜底，失败返回友好错误，别让脏数据进 /apply。

## 7. 错误处理

| 出错环节 | 处理策略 |
|---------|---------|
| /parse 失败（损坏/非pptx/加密） | 返回 4xx + 明确原因，Dify 结束并提示换文件 |
| LLM 输出非法 JSON | 代码节点 try-parse，失败重试 1 次，仍失败友好报错 |
| LLM 编造 ID | /apply 校验拦截 → rejected[]，其余照常应用 |
| 指令越界（r/c 超范围、删不存在页） | 单条 reject，不影响整体 |
| dup 顺序错（先 set_text 后 dup） | 临时 ID 找不到 → reject 该条 |
| 回写后文件异常 | /apply 生成后重新打开校验，失败整体回滚报错 |

**总原则**：能局部拒绝就别整体失败，每次都把 rejected[] 透传回用户。

## 8. 测试策略

### PPT 服务（TDD）

| 层级 | 测什么 | 怎么测 |
|------|--------|--------|
| 解析 | 各类形状/占位符/表格正确抽成 JSON | 3~4 个样例 pptx 做 fixture，断言字段 |
| 回写 | 5 条指令各自正确应用 | 每条独立用例：应用后重新解析断言 |
| 往返 | parse→apply→parse 一致性 | 黄金用例：改文字+复制页+删页，验证结构 |
| 校验 | 非法指令被正确 reject | 喂坏指令，断言进 rejected 且不污染好指令 |

### LLM 节点（评估用例，非确定性）

准备「模板 + 需求 → 期望指令类型」case，跑通后人工抽检：是否编造 ID、dup 顺序、是否乱改样式。

### 端到端

真实模板走完整链路，肉眼验收下载的 pptx：样式没走样、内容对、页数对。

## 9. 实现顺序（降风险）

```
1. PPT服务 /parse        ← 先能把 pptx 变 JSON，TDD
2. PPT服务 /apply 5条指令  ← 再能按指令回写，TDD，最核心
3. 本地脚本串 parse→手写ops→apply  ← 不接LLM先验证机械链路通
4. 接入 Dify + LLM 调通    ← 最后加"大脑"
5. 真实模板端到端验收
```

**关键**：第 3 步先用手写指令验证服务正确，再接 LLM——把"机械正确性"和"LLM 识别质量"两个问题彻底分开，调试不打架。

## 10. v2 待办（明确不在 v1 范围）

- 图片替换、配色/样式调整指令
- 长 PPT 的分批/分页处理
- 存储上云（OSS/S3 + Redis）
- 方案 3 视觉增强（渲染缩略图给多模态模型辅助识别）
