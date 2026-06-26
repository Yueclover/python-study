# PPT Editor Service

把 PPT 模板解析为带 ID 的 JSON，并按编辑指令回写 pptx。

## 运行
```bash
pip install -r requirements.txt
playwright install chromium   # 首次需安装无头浏览器（约 +400MB）
PPT_STORAGE=./storage uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 接口
- POST /parse  (multipart file) -> {doc_id, slide_size, slides}
- POST /apply  ({doc_id, ops})  -> {download_url, applied, rejected}
- GET  /files/{name}            -> pptx 附件
- POST /validate  ({html}) -> {bad_pages:[{page,type,detail}]}  渲染校验溢出/重叠

## 指令集（v1）
set_text / set_cell / set_table_size / dup_slide / del_slide

（详见 docs/superpowers/specs/2026-06-18-ppt-template-llm-edit-design.md）
