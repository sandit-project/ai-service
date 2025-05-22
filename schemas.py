# ai-service/schemas.py
from typing import List, Optional
from pydantic import BaseModel, Field

class SaveAllergyReq(BaseModel):
    user_uid: Optional[int] = None
    allergies: List[str]


class AllergyList(BaseModel):
    allergy: List[str]

class AllergyCheckReq(BaseModel):
    user_uid: Optional[int] = None
    social_uid: Optional[int] = None
    allergy: List[str] = Field(default_factory=list)
    ingredients: List[str] = Field(...)

class AllergyCheckRes(BaseModel):
    risk: bool
    cause: List[str]
    detail: str