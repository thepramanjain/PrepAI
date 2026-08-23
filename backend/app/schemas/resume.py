"""
app/schemas/resume.py

Pydantic schemas for Resume API requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import PyObjectId


class ResumeResponse(BaseModel):
    id: PyObjectId = Field(validation_alias="_id")
    filename: str
    file_type: str
    file_size: int
    text_length: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class ResumeDetailResponse(ResumeResponse):
    extracted_text: str


class ResumeListResponse(BaseModel):
    resumes: list[ResumeResponse]
    total: int
    page: int
    limit: int
