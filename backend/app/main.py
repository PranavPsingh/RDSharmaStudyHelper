import base64
import hashlib
import json
import threading
from contextlib import asynccontextmanager
from secrets import compare_digest

from cryptography.fernet import Fernet, InvalidToken
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .chapters import BY_ID, CHAPTERS
from .generator import generate_questions
from .planner import build_plan
from .pdf_loader import chapter_text
from .schemas import (
    AnswersRequest,
    AnswersResponse,
    GenerateRequest,
    GenerateResponse,
    QuestionAnswer,
)

_ANSWER_PASSWORD = "PranayRaj@2005"
_ANSWER_SET_TTL_SECONDS = 30 * 60
_ANSWER_CIPHER = Fernet(
    base64.urlsafe_b64encode(hashlib.sha256(_ANSWER_PASSWORD.encode()).digest())
)


def _warm_chapter_cache() -> None:
    for chapter in CHAPTERS:
        try:
            chapter_text(chapter.id)
        except Exception:  # PDF cache warming is best-effort during startup.
            pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    threading.Thread(target=_warm_chapter_cache, daemon=True).start()
    yield


app = FastAPI(title="Class X Maths Study Helper", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/chapters")
def list_chapters():
    return [
        {
            "id": c.id,
            "label": c.label,
            "title": c.title,
            "unit": c.unit,
            "weight_pct": c.weight_pct,
        }
        for c in CHAPTERS
    ]


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    if req.chapter_id is not None and req.chapter_id not in BY_ID:
        raise HTTPException(status_code=400, detail=f"Unknown chapter {req.chapter_id}")

    plan = build_plan(req.chapter_id)
    try:
        questions = generate_questions(plan)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    answers = [
        QuestionAnswer(slot=q.slot, solution=q.solution, final_answer=q.final_answer)
        for q in questions
    ]
    answer_token = _ANSWER_CIPHER.encrypt(
        AnswersResponse(answers=answers).model_dump_json().encode()
    ).decode()

    return GenerateResponse(
        mode="chapter" if req.chapter_id is not None else "all",
        total_marks=sum(q.marks for q in questions),
        answer_token=answer_token,
        questions=[
            {
                "slot": q.slot,
                "chapter_id": q.chapter_id,
                "chapter_label": q.chapter_label,
                "chapter_title": q.chapter_title,
                "chapter_weight_pct": q.chapter_weight_pct,
                "difficulty": q.difficulty,
                "marks": q.marks,
                "question": q.question,
                "diagram_svg": q.diagram_svg,
                "diagram_alt": q.diagram_alt,
            }
            for q in questions
        ],
    )


@app.post("/api/answers", response_model=AnswersResponse)
def get_answers(req: AnswersRequest):
    if not compare_digest(req.password, _ANSWER_PASSWORD):
        raise HTTPException(status_code=401, detail="Incorrect password")

    try:
        payload = _ANSWER_CIPHER.decrypt(
            req.answer_token.encode(),
            ttl=_ANSWER_SET_TTL_SECONDS,
        )
    except InvalidToken as exc:
        raise HTTPException(
            status_code=404,
            detail="Question set expired or invalid; generate a new set",
        ) from exc

    return AnswersResponse.model_validate_json(payload)
