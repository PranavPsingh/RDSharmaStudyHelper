import logging
import random
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import TypeVar
from xml.etree import ElementTree

from google import genai
from google.genai import types

from .chapters import BY_ID
from .config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_THINKING_BUDGET, MAX_PARALLEL_CALLS
from .pdf_loader import chapter_excerpt
from .planner import MARKS, Slot
from .schemas import GeneratedDiagram, GeneratedQuestion, GeneratedSet, QuestionOut
from .svg_sanitize import sanitize_svg

_client: genai.Client | None = None
_client_lock = Lock()
_logger = logging.getLogger("uvicorn.error")
TRANSIENT_RETRY_ATTEMPTS = 5
T = TypeVar("T")

DIFFICULTY_GUIDE = {
    "easy": "direct application of a single formula or definition; 1 mark; solvable in under a minute.",
    "medium": "2-3 steps combining two ideas, similar to a typical textbook exercise; 3 marks.",
    "hard": "multi-step, requires insight or combining several concepts, similar to a 5-mark CBSE "
    "long-answer or case-based question; 5 marks.",
}


def _client_instance() -> genai.Client:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                if not GEMINI_API_KEY:
                    raise RuntimeError("GEMINI_API_KEY is not set. Add it to .env.")
                _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _build_prompt(
    plan: list[Slot],
    phase: float = 0.0,
    avoid_questions: list[str] | None = None,
) -> str:
    chapter_ids = sorted({s.chapter_id for s in plan})
    sources = "\n\n".join(
        f"=== SOURCE: Chapter {cid} - {BY_ID[cid].title} ===\n"
        f"{chapter_excerpt(cid, phase=phase)}"
        for cid in chapter_ids
    )
    slots = "\n".join(
        f"- slot {s.slot}: chapter {s.chapter_id} ({BY_ID[s.chapter_id].title}), "
        f"difficulty {s.difficulty.upper()} - {DIFFICULTY_GUIDE[s.difficulty]}"
        for s in plan
    )
    avoid_section = ""
    if avoid_questions:
        avoid_list = "\n".join(f"- {question}" for question in avoid_questions)
        avoid_section = f"""
Do not repeat or lightly rephrase any of these questions:
{avoid_list}
"""
    return f"""You are a CBSE Class X mathematics teacher writing a practice set for a student.

Below are samples from the NCERT textbook chapters. They contain worked examples and exercise
questions. Study their style, notation and level, then write NEW questions. The excerpts are only
samples, so any topic from the named chapter may be used. Do not copy any question from the book;
change the numbers, contexts and structure.

Write exactly {len(plan)} questions, one for each slot below. Each question must be about the
chapter named in its slot and match its difficulty. Make every question in this set distinct;
do not repeat a question or create a lightly reworded version of another question.

{slots}
{avoid_section}

Rules:
- Stay within the textbook's syllabus for that chapter.
- Every question must be solvable and have one correct final answer. Verify your arithmetic.
- Write maths in plain text/unicode (e.g. x^2, sqrt(3), π, ≤). No LaTeX, no markdown.
- "solution" must be a complete, easy-to-follow school-textbook worked solution, not a summary.
  Show every meaningful step needed to get from the question to the result; do not skip algebra,
  arithmetic, substitutions, or reasoning with phrases such as "after simplification" or "similarly".
  State the formula, theorem, or method being used, substitute the given values, show intermediate
  calculations and transformations on separate lines, and explain why each non-obvious step follows.
  For proofs, give each inference with its reason. Keep units with quantities and include a check
  of the result where practical. Number the working as "Step 1:", "Step 2:", etc. Use enough steps
  for the question's difficulty: concise but complete for 1-mark questions, and progressively more
  detailed for 3- and 5-mark questions. "final_answer" is only the clearly stated result, not the
  working.
- Return the slot number with each question.

DIAGRAMS. For each question decide whether a figure is needed. Add one when the question refers
to a shape or picture: triangles (similar triangles, right triangles, trig ratios), circles
(tangents, chords, arcs, sectors, segments), combinations of solids, heights-and-distances
problems (angle of elevation/depression with a tower, building or ladder), points or lines on a
coordinate plane, graphs of polynomials or of pairs of linear equations. Do NOT add one for pure
arithmetic or algebra, probability with no picture, statistics tables, or proofs. If a figure is
needed, put the complete SVG in diagram_svg and a one-sentence description in diagram_alt;
otherwise leave both null.
Rules for the SVG:
- Black and white only: stroke black, fill white or none. No colours, gradients or shadows. Thin
  black hatching is allowed.
- Root element <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H"> with W <= 500 and H <=
  400. stroke-width 1.5 to 2. Text uses font-family sans-serif, font-size 14 to 16.
- Show every detail the question gives and nothing else: label vertices and points with capital
  letters; write given lengths, radii, angles and heights next to the correct segments; mark
  right angles with a small square; mark equal sides or angles with tick marks or arcs; use dashed
  lines for auxiliary or hidden edges; mark parallel lines with matching arrows; for coordinate
  or graph questions draw the axes with tick labels. Include every number, unit, and algebraic
  expression given in the question and place it by the correct segment or point. The degree symbol
  (°) may be used instead of the word "degrees".
- Before returning a diagram, check every label against the question. Never omit or alter given
  measurements, invent measurements, or substitute one expression for another. If a faithful
  diagram cannot be made, leave diagram_svg and diagram_alt null.
- Do NOT reveal the answer. An unknown quantity is drawn as a letter (x, h) or "?", never its
  value.
- Draw to scale as far as the given numbers allow: choose coordinates so side ratios and angles
  match the stated values (a 3-4-5 triangle really is 3:4:5, a 30 degree angle really looks like
  30 degrees).
- Keep labels from overlapping lines or each other.
- Use only these elements: svg, g, line, polyline, polygon, path, circle, ellipse, rect, text,
  tspan, defs, marker. No scripts, images, links, <style> or event handlers.
- The question text must still contain all the numeric data, so it can be solved without the
  picture. "In the figure" alone is not enough.
Example of the expected style (right triangle ABC, right angle at B, AB = 3 cm, BC = 4 cm, find
AC = x):
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 240" stroke="black" fill="none"
stroke-width="2" font-family="sans-serif" font-size="16"><polygon points="70,40 70,190
270,190"/><polyline points="70,170 90,170 90,190" stroke-width="1.5"/><g fill="black"
stroke="none"><text x="52" y="40">A</text><text x="52" y="208">B</text><text x="276"
y="208">C</text><text x="64" y="120" text-anchor="end">3 cm</text><text x="160" y="212">4
cm</text><text x="180" y="105">x</text></g></svg>

{sources}
"""


def _generate_once(
    plan: list[Slot],
    phase: float = 0.0,
    avoid_questions: list[str] | None = None,
) -> GeneratedSet:
    response = _client_instance().models.generate_content(
        model=GEMINI_MODEL,
        contents=_build_prompt(plan, phase=phase, avoid_questions=avoid_questions),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeneratedSet,
            temperature=0.9,
            **(
                {"thinking_config": types.ThinkingConfig(thinking_budget=GEMINI_THINKING_BUDGET)}
                if GEMINI_THINKING_BUDGET is not None
                else {}
            ),
        ),
    )
    parsed = response.parsed
    if parsed is None:
        raise ValueError("Gemini returned no parseable output")
    return parsed


def _question_key(question: str) -> str:
    return re.sub(r"\s+", " ", question).strip().casefold()


def _is_transient_gemini_error(exc: Exception) -> bool:
    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if status_code in {500, 502, 503, 504}:
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    message = str(exc).upper()
    return any(
        marker in message
        for marker in (
            "500 INTERNAL",
            "502 BAD_GATEWAY",
            "502 BAD GATEWAY",
            "503 UNAVAILABLE",
            "503 SERVICE_UNAVAILABLE",
            "503 SERVICE UNAVAILABLE",
            "504 DEADLINE_EXCEEDED",
            "504 GATEWAY_TIMEOUT",
            "504 GATEWAY TIMEOUT",
        )
    )


def _with_transient_retries(operation: Callable[[], T], operation_name: str) -> T:
    for attempt in range(TRANSIENT_RETRY_ATTEMPTS):
        try:
            return operation()
        except Exception as exc:
            if not _is_transient_gemini_error(exc) or attempt == TRANSIENT_RETRY_ATTEMPTS - 1:
                raise

            delay = min(2**attempt, 8)
            delay += random.uniform(0, delay * 0.25)
            _logger.warning(
                "%s failed with a transient Gemini error (attempt %d/%d); retrying in %.1f seconds: %s",
                operation_name,
                attempt + 1,
                TRANSIENT_RETRY_ATTEMPTS,
                delay,
                exc,
            )
            time.sleep(delay)


def _question_requires_diagram(question: str) -> bool:
    return re.search(
        r"\b(?:triangle|trapez(?:ium|oid)|quadrilateral|circle|tangent|chord|arc|sector|"
        r"segment|cone|sphere|cylinder|hemisphere|cuboid|cube|solid|height|tower|building|"
        r"pole|ladder|shadow|balloon|coordinate|graph|axes|plot)\b|"
        r"\bangle of (?:elevation|depression)\b",
        question,
        re.IGNORECASE,
    ) is not None


def _normalize_math_label(value: str) -> str:
    value = value.casefold().replace("−", "-").replace("–", "-").replace("×", "*")
    value = value.replace("°", " degrees ").replace("º", " degrees ")
    value = re.sub(r"\bdeg(?:ree)?s?\b", "degrees", value)
    value = re.sub(r"\bsqrt\s*\(", "√(", value)
    value = re.sub(r"\s+", "", value)
    return value.rstrip(".,;:")


def _given_measurements(question: str) -> list[str]:
    measurements = []
    segments = re.split(r",|;\s*|\band\s+(?=[A-Z]{1,3}\s*=)", question)
    for segment in segments:
        assignment = re.search(r"\b[A-Z]{1,3}\s*=\s*(.+)", segment)
        if assignment is None:
            continue
        value = assignment.group(1).strip()
        value = re.split(r"\b(?:and hence|and find|find|determine|calculate)\b", value, maxsplit=1, flags=re.I)[0]
        value = value.rstrip(" .?!")
        if value:
            measurements.append(value)
    return measurements


def _diagram_missing_measurements(question: str, svg: str) -> list[str]:
    try:
        root = ElementTree.fromstring(svg)
    except ElementTree.ParseError:
        return _given_measurements(question)

    labels = [
        _normalize_math_label("".join(node.itertext()))
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] == "text"
    ]
    return [
        measurement
        for measurement in _given_measurements(question)
        if not any(_normalize_math_label(measurement) in label for label in labels)
    ]


def _duplicate_slots(plan: list[Slot], questions: dict[int, GeneratedQuestion]) -> list[Slot]:
    seen: set[str] = set()
    duplicates = []
    for slot in plan:
        key = _question_key(questions[slot.slot].question)
        if key in seen:
            duplicates.append(slot)
        else:
            seen.add(key)
    return duplicates


def _generate_batch(
    plan: list[Slot],
    phase: float,
    batch_number: int,
    avoid_questions: list[str] | None = None,
) -> dict[int, GeneratedQuestion]:
    expected = {s.slot for s in plan}
    last_error: Exception | None = None
    started_at = time.perf_counter()
    avoid_questions = list(avoid_questions or [])

    for _ in range(2):  # one retry if the model skips or repeats a slot
        by_slot: dict[int, GeneratedQuestion] = {}
        try:
            result = _with_transient_retries(
                lambda: _generate_once(plan, phase=phase, avoid_questions=avoid_questions),
                f"Gemini batch {batch_number}",
            )
            by_slot = {q.slot: q for q in result.questions}
            if len(result.questions) != len(expected) or set(by_slot) != expected:
                raise ValueError(f"Expected slots {sorted(expected)}, got {sorted(by_slot)}")
            duplicate_slots = _duplicate_slots(plan, by_slot)
            avoid_keys = {_question_key(question) for question in avoid_questions}
            duplicate_slots.extend(
                slot
                for slot in plan
                if _question_key(by_slot[slot.slot].question) in avoid_keys
                and slot not in duplicate_slots
            )
            if duplicate_slots:
                duplicate_numbers = sorted({slot.slot for slot in duplicate_slots})
                raise ValueError(f"Repeated question text in slots {duplicate_numbers}")
            _logger.info(
                "Gemini batch %d completed in %.2f seconds",
                batch_number,
                time.perf_counter() - started_at,
            )
            return {slot: by_slot[slot] for slot in expected}
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if len(by_slot) == len(expected):
                avoid_questions.extend(q.question for q in by_slot.values())
            if _is_transient_gemini_error(exc):
                break
    _logger.info(
        "Gemini batch %d failed after %.2f seconds",
        batch_number,
        time.perf_counter() - started_at,
    )
    raise RuntimeError(f"Question generation failed for batch {batch_number}: {last_error}")


def _generate_diagram(question: str, batch_number: int) -> tuple[str | None, str | None]:
    measurements = _given_measurements(question)
    required_labels = "\n".join(f"- {measurement}" for measurement in measurements) or "- Every stated geometric measurement"
    prompt = f"""Create a black-and-white SVG diagram for this exact question. Do not change or
paraphrase the question, add measurements, or solve it. Use the question as the only source of
    truth. Put each given measurement beside the correct segment, point, or angle, preserving its
    number and unit (the degree symbol ° is equivalent to the word "degrees"). Never put a
    solved/unknown value in the diagram. Return null for both fields only if a faithful diagram cannot
    be made.

Given measurements that must appear exactly:
{required_labels}

Use root <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H"> with W <= 500 and H <= 400.
Use stroke black, fill white or none, stroke-width 1.5 to 2, sans-serif text size 14 to 16.
Only use svg, g, line, polyline, polygon, path, circle, ellipse, rect, text, tspan, defs, marker.
Label vertices and points with capital letters; include right-angle markers and dashed auxiliary
lines where appropriate. No scripts, images, links, styles, or event handlers.

Question:
{question}
"""
    last_error: Exception | None = None
    for _ in range(2):
        try:
            response = _with_transient_retries(
                lambda: _client_instance().models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=GeneratedDiagram,
                        temperature=0.2,
                        **(
                            {"thinking_config": types.ThinkingConfig(thinking_budget=GEMINI_THINKING_BUDGET)}
                            if GEMINI_THINKING_BUDGET is not None
                            else {}
                        ),
                    ),
                ),
                f"Diagram generation batch {batch_number}",
            )
            parsed = response.parsed
            if parsed is None or parsed.diagram_svg is None:
                raise ValueError("Gemini did not return a diagram")
            sanitized = sanitize_svg(parsed.diagram_svg)
            if sanitized is None:
                raise ValueError("Gemini returned invalid SVG")
            missing = _diagram_missing_measurements(question, sanitized)
            if missing:
                raise ValueError(f"Diagram omits given measurement(s): {missing}")
            if not parsed.diagram_alt:
                raise ValueError("Gemini did not return diagram_alt")
            return sanitized, parsed.diagram_alt
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if _is_transient_gemini_error(exc):
                break
    _logger.warning("Diagram batch %d regeneration failed: %s", batch_number, last_error)
    raise RuntimeError(f"Could not create a faithful diagram: {last_error}")


def generate_questions(plan: list[Slot]) -> list[QuestionOut]:
    total_started_at = time.perf_counter()
    try:
        if not plan:
            return []

        n = min(MAX_PARALLEL_CALLS, len(plan))
        batches = [plan[i::n] for i in range(n)]
        generated_by_slot = {}
        with ThreadPoolExecutor(max_workers=n) as executor:
            futures = [
                executor.submit(_generate_batch, batch, i / n, i + 1)
                for i, batch in enumerate(batches)
            ]
            for future in futures:
                generated_by_slot.update(future.result())

        for attempt in range(3):
            duplicate_slots = _duplicate_slots(plan, generated_by_slot)
            if not duplicate_slots:
                break
            if attempt == 2:
                duplicate_numbers = [slot.slot for slot in duplicate_slots]
                raise RuntimeError(
                    f"Question generation produced repeated questions for slots "
                    f"{duplicate_numbers} after regeneration."
                )

            avoid_questions = [
                generated_by_slot[slot.slot].question
                for slot in plan
                if slot not in duplicate_slots
            ]
            _logger.warning(
                "Regenerating repeated question(s) in slots %s",
                [slot.slot for slot in duplicate_slots],
            )
            replacements = _generate_batch(
                duplicate_slots,
                phase=(attempt + 1) / 4,
                batch_number=n + attempt + 1,
                avoid_questions=avoid_questions,
            )
            generated_by_slot.update(replacements)

        out = []
        for s in plan:
            q = generated_by_slot[s.slot]
            ch = BY_ID[s.chapter_id]
            diagram_svg = sanitize_svg(q.diagram_svg)
            diagram_alt = q.diagram_alt if diagram_svg is not None else None
            needs_diagram = _question_requires_diagram(q.question)
            if diagram_svg is not None:
                missing_measurements = _diagram_missing_measurements(q.question, diagram_svg)
                if missing_measurements or (needs_diagram and not diagram_alt):
                    _logger.warning(
                        "Question slot %d diagram is incomplete (missing measurements: %s); regenerating",
                        s.slot,
                        missing_measurements,
                    )
                    diagram_svg = None
                    diagram_alt = None
            if q.diagram_svg is not None and diagram_svg is None:
                _logger.warning("Discarded invalid or inconsistent diagram for question slot %d", s.slot)
            if needs_diagram and diagram_svg is None:
                _logger.info("Generating a replacement diagram for question slot %d", s.slot)
                diagram_svg, diagram_alt = _generate_diagram(q.question, n + s.slot)
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
                    diagram_svg=diagram_svg,
                    diagram_alt=diagram_alt,
                )
            )
        return out
    finally:
        _logger.info("Generated question set in %.2f seconds", time.perf_counter() - total_started_at)
