"""
app/schemas/question.py

Pydantic schemas for interview questions.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import PyObjectId
from app.schemas.interview import Difficulty


class QuestionCreate(BaseModel):
    question: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    difficulty: Difficulty


class QuestionResponse(BaseModel):
    id: PyObjectId = Field(validation_alias="_id")
    interview_id: PyObjectId
    question_number: int
    question: str
    category: str
    difficulty: Difficulty
    source: str = "manual"
    question_type: str = "primary"
    parent_question_id: Optional[PyObjectId] = None
    created_at: datetime

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class QuestionListResponse(BaseModel):
    items: List[QuestionResponse]
