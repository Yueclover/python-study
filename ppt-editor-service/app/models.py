from typing import Any
from pydantic import BaseModel


class ApplyRequest(BaseModel):
    doc_id: str
    ops: list[dict[str, Any]]


class ApplyPlanRequest(BaseModel):
    doc_id: str
    plan: list[dict[str, Any]]
