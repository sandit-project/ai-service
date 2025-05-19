# ai-service/schemas.py
from typing import List
from pydantic import BaseModel

class AllergyList(BaseModel):
    allergy: List[str]

class AllergyCheckReq(BaseModel):
    user_id: int
    ingredients: List[str]

class AllergyCheckRes(BaseModel):
    risk: bool
    cause: List[str]
    detail: str