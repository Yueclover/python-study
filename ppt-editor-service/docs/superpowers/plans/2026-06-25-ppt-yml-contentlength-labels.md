# PPT yml 篇幅控制 + 残留标签修复 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `ppt-template-llm-edit.yml` 加 `content_length` 篇幅档位控制正文页数，并修掉每页残留的模板章节标签。

**Architecture:** 纯改 yml（一个 start 新变量 + 三处 prompt 文本），不改 graph 结构、不改 Python 代码。用一个一次性校验脚本充当"测试"，保证改动后 YAML 可解析且关键引用存在、原结构未被破坏。

**Tech Stack:** Dify workflow DSL (YAML)、Python `PyYAML`（已随 python-pptx 环境可用）。

## Global Constraints

- 只编辑这一个文件：`ppt-editor-service/dify/ppt-template-llm-edit.yml`。
- 不新增/删除节点(node)与边(edge)，不改 `graph.edges`、不改任何 `code` 节点。
- 篇幅→正文页数映射，全流程统一：`short→8`、`normal→14`、`long→20`，空值按 `normal`。
- `content_length` 为选填，默认 `normal`。
- 不在范围内：TOC 项数对齐、章节过渡页、`skeleton.py` role 识别。
- 验证脚本是临时文件，完成后删除，不提交。

---

### Task 1: 校验脚本（充当测试）

**Files:**
- Create(临时，不提交): `ppt-editor-service/scripts/_check_yml.py`
- Target: `ppt-editor-service/dify/ppt-template-llm-edit.yml`

**Interfaces:**
- Produces: 命令 `python scripts/_check_yml.py`，全部断言通过时打印 `ALL CHECKS PASSED`，
  否则在第一个失败处抛 `AssertionError`。后续 Task 2–4 都用它验证。

- [ ] **Step 1: 写校验脚本**

```python
# ppt-editor-service/scripts/_check_yml.py  (临时文件，勿提交)
import yaml, sys

P = "dify/ppt-template-llm-edit.yml"
with open(P, encoding="utf-8") as f:
    doc = yaml.safe_load(f)

g = doc["workflow"]["graph"]
nodes = {n["id"]: n for n in g["nodes"]}
edges = g["edges"]

# --- 结构完整性：节点/边数量与现状一致（基线 10 节点 / 10 边）---
assert len(g["nodes"]) == 10, ("node count changed: %d" % len(g["nodes"]))
assert len(edges) == 10, ("edge count changed: %d" % len(edges))

def node_text(nid):
    return yaml.dump(nodes[nid]["data"], allow_unicode=True)

# --- Task 2: start 新增 content_length 选填变量 ---
start_vars = nodes["start"]["data"]["variables"]
cl = [v for v in start_vars if v.get("variable") == "content_length"]
assert cl, "start missing content_length variable"
cl = cl[0]
assert cl.get("required") is False, "content_length should be optional"
assert cl.get("type") == "select", "content_length should be select"
for opt in ("short", "normal", "long"):
    assert opt in (cl.get("options") or []), "missing option %s" % opt

# --- Task 3: 两个大纲节点引用 content_length 且含映射数字 ---
for nid in ("17817757512960", "llm_a"):
    t = node_text(nid)
    assert "content_length" in t, "%s missing content_length ref" % nid
    assert "8" in t and "14" in t and "20" in t, "%s missing page mapping" % nid

# --- Task 4: 填充节点不再保留章节标签原值 ---
fill = node_text("llm_fill_all")
assert "装饰性固定文字保持" not in fill, "old keep-rule still present"
assert "栏目" in fill or "章节标题" in fill, "new rewrite rule missing"

print("ALL CHECKS PASSED")
```

- [ ] **Step 2: 运行，确认现在是 FAIL（基线尚未改）**

Run: `cd ppt-editor-service && python scripts/_check_yml.py`
Expected: 在 `content_length` 断言处 `AssertionError: start missing content_length variable`
（先确认结构断言 node==10 / edge==10 通过；若数量不符，先核对基线再继续）。

---

### Task 2: start 新增 content_length 选填变量

**Files:**
- Modify: `ppt-editor-service/dify/ppt-template-llm-edit.yml` （start 节点 `data.variables`，约 207–212 行 `user_brief` 之后）

- [ ] **Step 1: 在 user_brief 变量之后追加 content_length**

在 `start` 节点 variables 数组里，`user_brief`（以 `variable: user_brief` 结尾）后新增：

```yaml
        - label: 篇幅
          type: select
          variable: content_length
          required: false
          default: normal
          options:
          - short
          - normal
          - long
```

（注意缩进与同数组其它项对齐：`- label:` 下属字段为 8 空格、列表项 `-` 为 10 空格，照抄上方 `user_brief` 项的缩进。）

- [ ] **Step 2: 运行校验，确认 content_length 断言已过、推进到大纲节点断言失败**

Run: `cd ppt-editor-service && python scripts/_check_yml.py`
Expected: `AssertionError: 17817757512960 missing content_length ref`

---

### Task 3: 两个大纲节点注入篇幅页数控制

**Files:**
- Modify: `ppt-editor-service/dify/ppt-template-llm-edit.yml`
  - 节点 `17817757512960`（"大纲"，system + user 文本，约 620–636 行）
  - 节点 `llm_a`（"大纲规划"，system + user 文本，约 323–347 行）

- [ ] **Step 1: 改 `17817757512960` 的 system 文本**

把该节点 `role: system` 的 `text` 改为：

```
你是PPT大纲规划师。根据用户需求规划要产出的每一页。
只输出 JSON，含 outline 数组，不要解释、不要代码块包裹。
篇幅控制：正文要点数量按"篇幅档位"决定——short≈8项、normal≈14项、long≈20项；档位为空或无法识别时按 normal(14)处理。封面/目录/结尾不计入该数量。
```

- [ ] **Step 2: 改 `17817757512960` 的 user 文本**

把该节点 `role: user` 的 `text` 改为：

```
篇幅档位：{{#start.content_length#}}
用户需求：
{{#start.user_brief#}}

请只输出 outline 的 JSON。
```

- [ ] **Step 3: 给 `llm_a` 的 system 文本追加第 5 条规则**

在 `llm_a` 节点 `role: system` 文本现有规则 4 之后、输出示例之前，插入一行：

```
5. 正文页数与篇幅档位匹配：short≈8页、normal≈14页、long≈20页（空值按 normal）；该计数不含封面/目录/过渡/结尾页。
```

- [ ] **Step 4: 给 `llm_a` 的 user 文本加篇幅档位引用**

把 `llm_a` 节点 `role: user` 文本改为（在"大纲"之后追加篇幅档位行）：

```
模板页面清单（slide_id 与 role）：
{{#code_extract.pages#}}

大纲：
{{#17817757512960.text#}}

篇幅档位：{{#start.content_length#}}

请只输出 outline 的 JSON。
```

- [ ] **Step 5: 运行校验，确认推进到填充节点断言失败**

Run: `cd ppt-editor-service && python scripts/_check_yml.py`
Expected: `AssertionError: old keep-rule still present`

---

### Task 4: 修填充节点的残留标签规则

**Files:**
- Modify: `ppt-editor-service/dify/ppt-template-llm-edit.yml` （节点 `llm_fill_all` 的 `role: system` 文本，规则 2，约 443–447 行）

- [ ] **Step 1: 替换规则 2**

把 `llm_fill_all` system 文本里的这一条：

```
2. 每个可编辑槽都要给出文本；页码/日期/装饰性固定文字保持其 current_text 原值。
```

替换为两条：

```
2. 每个可编辑槽都要给出文本。仅以下内容保持 current_text 原值：页码数字(如01-05)、日期、品牌口号"专 注 AI   探 索未 来"、"目录/CONTENTS"、"感谢观看"。
3. 栏目/章节标题类文字（如模板里的"创新与成长""三季度工作完成情况""存在主要问题""四季度工作规划""想法和建议"）必须按本页 brief 改写成贴合本页主题的简短标签，不得保留模板原值。
```

（原规则 3、4 顺延为 4、5；若担心编号混乱，可只在文中说明、不强求重排序号——校验脚本只检查"装饰性固定文字保持"已消失且出现"栏目"/"章节标题"。）

- [ ] **Step 2: 运行校验，确认全部通过**

Run: `cd ppt-editor-service && python scripts/_check_yml.py`
Expected: `ALL CHECKS PASSED`

---

### Task 5: 收尾 — diff、清理、提交

- [ ] **Step 1: 删除临时校验脚本**

```bash
rm ppt-editor-service/scripts/_check_yml.py
```

- [ ] **Step 2: 给用户看 diff（不自动提交，等用户确认）**

```bash
git -C ppt-editor-service diff -- dify/ppt-template-llm-edit.yml
```

- [ ] **Step 3: 用户确认后提交**

```bash
git add ppt-editor-service/dify/ppt-template-llm-edit.yml
git commit -m "feat(dify): add content_length page control + fix residual section labels"
```

---

## Self-Review

- **Spec coverage:** 改动1(content_length 输入)=Task 2；改动2(页数控制注入两节点)=Task 3；改动3(残留标签)=Task 4；验证=Task 1+各步校验=Task 5 diff。✅ 全覆盖。
- **Placeholder scan:** 各步均含可直接粘贴的具体文本/命令，无 TBD。✅
- **Type consistency:** 校验脚本里的节点 id（`start`/`17817757512960`/`llm_a`/`llm_fill_all`）与 yml 实际 id 一致；篇幅数字 8/14/20 全程统一。✅
- **基线核对:** 已实测 node==10 / edge==10、start 现有变量 `file`/`user_brief`，脚本断言与之一致。✅
