import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .chapters import BY_ID, CHAPTERS
from .generator import generate_questions
from .planner import build_plan
from .pdf_loader import chapter_text
from .schemas import GenerateRequest, GenerateResponse


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

    return GenerateResponse(
        mode="chapter" if req.chapter_id is not None else "all",
        total_marks=sum(q.marks for q in questions),
        questions=questions,
    )
