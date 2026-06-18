import os

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pptx import Presentation

from .storage import Storage, valid_doc_id
from .parser import parse_presentation
from .applier import apply_ops
from .models import ApplyRequest

app = FastAPI(title="PPT Editor Service")
storage = Storage(os.environ.get("PPT_STORAGE", "./storage"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse")
async def parse_endpoint(file: UploadFile = File(...)):
    data = await file.read()
    doc_id = storage.new_doc(data)
    try:
        prs = Presentation(storage.source_path(doc_id))
    except Exception:
        raise HTTPException(status_code=400, detail="无法解析 pptx 文件")
    result = parse_presentation(prs)
    result["doc_id"] = doc_id
    return result


@app.post("/apply")
def apply_endpoint(req: ApplyRequest):
    if not valid_doc_id(req.doc_id) or not storage.exists(req.doc_id):
        raise HTTPException(status_code=404, detail="doc_id 不存在")
    prs = Presentation(storage.source_path(req.doc_id))
    applied, rejected = apply_ops(prs, req.ops)
    out = storage.output_path(req.doc_id)
    prs.save(out)
    try:
        Presentation(out)  # 输出有效性校验
    except Exception:
        raise HTTPException(status_code=500, detail="生成的 pptx 校验失败")
    name = os.path.basename(out)
    return {"download_url": f"/files/{name}", "applied": applied, "rejected": rejected}


@app.get("/files/{name}")
def download(name: str):
    doc_id = name.split("-out")[0]
    if not valid_doc_id(doc_id):
        raise HTTPException(status_code=404, detail="文件不存在")
    path = storage.output_path(doc_id)
    if not (os.path.basename(path) == name and os.path.isfile(path)):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        path,
        filename=name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
