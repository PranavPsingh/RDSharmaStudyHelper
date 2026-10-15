from google import genai
from google.genai import types

from .chapters import BY_ID
from .config import GEMINI_API_KEY, GEMINI_MODEL
from .pdf_loader import chapter_text
from .planner import MARKS, Slot
from .schemas import GeneratedSet, QuestionOut

_client: genai.Client | None = None

DIFFICULTY_GUIDE = {
    "easy": "direct application of a single formula or definition; 1 mark; solvable in under a minute.",
    "medium": "2-3 steps combining two ideas, similar to a typical textbook exercise; 3 marks.",
    "hard": "multi-step, requires insight or combining several concepts, similar to a 5-mark CBSE "
    "long-answer or case-based question; 5 marks.",
}


def _client_instance() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to .env.")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _build_prompt(plan: list[Slot]) -> str:
    chapter_ids = sorted({s.chapter_id for s in plan})
    sources = "\n\n".join(
        f"=== SOURCE: Chapter {cid} - {BY_ID[cid].title} ===\n{chapter_text(cid)}"
        for cid in chapter_ids
    )
    slots = "\n".join(
        f"- slot {s.slot}: chapter {s.chapter_id} ({BY_ID[s.chapter_id].title}), "
        f"difficulty {s.difficulty.upper()} - {DIFFICULTY_GUIDE[s.difficulty]}"
        for s in plan
    )
    return f"""You are a CBSE Class X mathematics teacher writing a practice set for a student.

Below is the text of the NCERT textbook chapters. It contains worked examples and exercise
questions. Study their style, notation and level, then write NEW questions. Do not copy any
question from the book; change the numbers, contexts and structure.

Write exactly {len(plan)} questions, one for each slot below. Each question must be about the
chapter named in its slot and match its difficulty.

{slots}

Rules:
- Stay within the textbook's syllabus for that chapter.
- Every question must be solvable and have one correct final answer. Verify your arithmetic.
- Write maths in plain text/unicode (e.g. x^2, sqrt(3), π, ≤). No LaTeX, no markdown.
- "solution" is a short step-by-step working. "final_answer" is just the answer.
- Return the slot number with each question.

{sources}
"""


def _generate_once(plan: list[Slot]) -> GeneratedSet:
    response = _client_instance().models.generate_content(
        model=GEMINI_MODEL,
        contents=_build_prompt(plan),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeneratedSet,
            temperature=0.9,
        ),
    )
    parsed = response.parsed
    if parsed is None:
        raise ValueError("Gemini returned no parseable output")
    return parsed


def generate_questions(plan: list[Slot]) -> list[QuestionOut]:
    expected = {s.slot for s in plan}
    last_error: Exception | None = None

    for _ in range(2):  # one retry if the model skips or repeats a slot
        try:
            result = _generate_once(plan)
            by_slot = {q.slot: q for q in result.questions}
            if set(by_slot) != expected:
                raise ValueError(f"Expected slots {sorted(expected)}, got {sorted(by_slot)}")
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    else:
        raise RuntimeError(f"Question generation failed: {last_error}")

    out = []
    for s in plan:
        q = by_slot[s.slot]
        ch = BY_ID[s.chapter_id]
        out.append(
            QuestionOut(
                slot=s.slot,
                chapter_id=ch.id,
                chapter_label=ch.label,
                chapter_title=ch.title,
                chapter_weight_pct=ch.weight_pct,
                difficulty=s.difficulty,
                marks=MARKS[s.difficulty],
                question=q.question,
                solution=q.solution,
                final_answer=q.final_answer,
            )
        )
    return out
