# Dify 工作流：PPT 模板 LLM 编辑

## 节点串联
```
[开始] file(文件) + user_brief(文本)
  → [HTTP-1 解析] POST {SVC}/parse，body 传 file
  → [LLM 生成指令] 输入 parse_result.slides + user_brief
  → [代码-校验] 解析 LLM 输出为 JSON、补 doc_id
  → [HTTP-2 回写] POST {SVC}/apply，body = {doc_id, ops}
  → [结束] 返回 download_url（+ rejected 提示）
```

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
```json
{"ops":[
  {"op":"set_text","shape_id":"s1_sh1","text":"2026 产品发布会"},
  {"op":"dup_slide","slide_id":"s2","count":3,"as":["d1","d2","d3"]},
  {"op":"set_text","shape_id":"d1::sh1","text":"要点一"},
  {"op":"set_text","shape_id":"d2::sh1","text":"要点二"},
  {"op":"set_text","shape_id":"d3::sh1","text":"要点三"},
  {"op":"del_slide","slide_id":"s3"}
]}
```

## LLM 节点 — User Prompt
模板结构（JSON）：
```
{{#parse_result.slides#}}
用户需求：
{{#start.user_brief#}}
请只输出 ops 的 JSON。
```

## 代码-校验节点（Python）
```python
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
```

- 若 valid=False：用条件分支走「失败提示」结束（提示用户重试或换模板）。
- 若 valid=True：把 payload 传给 HTTP-2。

## HTTP-2 回写节点
- Method: POST，URL: {SVC}/apply
- Body: JSON = 代码节点的 payload（{doc_id, ops}）
- 输出：download_url、applied、rejected

## 结束节点
- 返回 download_url；若 rejected 非空，附「部分指令未生效」提示并列出 rejected。
