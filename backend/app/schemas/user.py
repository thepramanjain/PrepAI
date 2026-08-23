"""
app/schemas/user.py

Pydantic schemas for user-related responses.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated


# Helper to convert MongoDB ObjectId to string for Pydantic
PyObjectId = Annotated[str, BeforeValidator(str)]


class UserResponse(BaseModel):
    """
    Public user representation.
    NEVER include password_hash here.
    """
    id: PyObjectId = Field(validation_alias="_id")
    name: str
    email: str
    target_role: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Allow mapping from _id to id
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
