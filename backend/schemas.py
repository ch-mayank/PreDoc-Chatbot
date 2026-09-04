"""Pydantic schemas for PreDoc API requests and responses."""

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class QueryRequest(BaseModel):
    """The symptom query payload sent by the frontend or client."""

    question: Optional[str] = Field(None, description="Clinical query / patient symptom text")
    message: Optional[str] = Field(None, description="Alternative field for symptom message")
    categories: Optional[List[str]] = Field(default_factory=list, description="Target medical specialties")
    age: Optional[str] = Field(None, description="Patient age / bracket")
    sex: Optional[str] = Field(None, description="Patient biological sex")

    @model_validator(mode="before")
    @classmethod
    def unify_query(cls, data: dict):
        if isinstance(data, dict):
            q = data.get("question") or data.get("message")
            if not q or len(str(q).strip()) < 2:
                raise ValueError("A valid 'question' or 'message' string must be provided.")
            data["question"] = str(q).strip()
        return data


class QueryResponse(BaseModel):
    """The structured answer returned to the client."""

    status: str = "success"
    authenticated_user: str = "clinical_guest"
    answer: str
    response: Optional[str] = None

    @model_validator(mode="after")
    def sync_response(self):
        if not self.response:
            self.response = self.answer
        return self
