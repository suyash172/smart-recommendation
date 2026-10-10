from fastapi import APIRouter
from pydantic import BaseModel

from app.services.name_service import to_english, names_match

router = APIRouter(prefix="/names", tags=["names"])


class NameIn(BaseModel):
    name: str


class MatchIn(BaseModel):
    name_a: str
    name_b: str


@router.post("/transliterate")
def transliterate(body: NameIn):
    return {"original": body.name, "english": to_english(body.name)}


@router.post("/match")
def match(body: MatchIn):
    ok, score = names_match(body.name_a, body.name_b)
    return {"is_match": ok, "score": score}