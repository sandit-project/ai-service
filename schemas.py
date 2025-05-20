# ai-service/schemas.py
from typing import List, Optional
from pydantic import BaseModel

class AllergyList(BaseModel):
    allergy: List[str]

class AllergyCheckReq(BaseModel):
    user_uid: Optional[int] = None
    social_uid: Optional[int] = None
    allergy: List[str] = []
    ingredients: List[str]

class AllergyCheckRes(BaseModel):
    risk: bool
    cause: List[str]
    detail: str