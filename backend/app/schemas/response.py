"""
app/schemas/response.py

Pydantic schemas for interview responses/answers.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import PyObjectId


class ResponseCreate(BaseModel):
    answer: str = Field(..., min_length=1)
    duration_seconds: Optional[int] = None


class ResponseResponse(BaseModel):
    id: PyObjectId = Field(validation_alias="_id")
    interview_id: PyObjectId
    question_id: PyObjectId
    user_id: PyObjectId
    answer: str
    answered_at: datetime
    duration_seconds: Optional[int] = None

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class ResponseListResponse(BaseModel):
    items: List[ResponseResponse]
