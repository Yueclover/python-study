from fastapi import FastAPI

app = FastAPI(title="PPT Editor Service")


@app.get("/health")
def health():
    return {"status": "ok"}
