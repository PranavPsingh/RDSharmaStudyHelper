import asyncio
import time
from threading import Lock
from types import SimpleNamespace

import pytest

from backend.app import generator
from backend.app.planner import Slot
from backend.app.schemas import DiagramReview, GeneratedDiagram, GeneratedQuestion


class InvalidArgumentError(Exception):
    code = 400


def test_invalid_argument_from_diagram_review_keeps_locally_valid_diagram(monkeypatch) -> None:
    plan = [Slot(1, 6, "easy")]
    svg = '<svg viewBox="0 0 100 100"><text>3 cm</text><text>4 cm</text></svg>'
    question = GeneratedQuestion(
        slot=1,
        question="In triangle ABC, if AB = 3 cm and BC = 4 cm, find AC.",
        solution="Working",
        final_answer="5 cm",
        diagram_svg=svg,
        diagram_alt="A triangle with AB and BC labelled.",
    )
    def generate_batch(batch, phase, batch_number, avoid_questions=None):
        del batch, phase, batch_number, avoid_questions
        return {1: question}

    monkeypatch.setattr(generator, "_generate_batch", generate_batch)

    def reject_review(**kwargs):
        del kwargs
        raise InvalidArgumentError("400 INVALID_ARGUMENT")

    monkeypatch.setattr(
        generator,
        "_client_instance",
        lambda: SimpleNamespace(models=SimpleNamespace(generate_content=reject_review)),
    )
    def unexpected_redraw(*args, **kwargs):
        del args, kwargs
        pytest.fail("review failure should not trigger a redraw")

    monkeypatch.setattr(generator, "_generate_diagram", unexpected_redraw)

    result = asyncio.run(generator.generate_questions(plan))

    assert result[0].diagram_svg == generator.sanitize_svg(svg)
    assert result[0].diagram_alt == "A triangle with AB and BC labelled."


def test_given_algebraic_measurements_are_extracted() -> None:
    question = (
        "In triangle ABC, if AD = 2x - 1 cm, DB = x + 3 cm, and AE = 2 cm, "
        "find EC."
    )

    assert generator._given_measurements(question) == ["2x - 1 cm", "x + 3 cm", "2 cm"]


def test_diagram_measurements_must_match_question_expressions() -> None:
    question = "In triangle ABC, if AD = 2x - 1 cm and DB = x + 3 cm, find EC."
    mismatched_svg = """<svg viewBox="0 0 100 100"><text>2x + 1 cm</text><text>x + 3 cm</text></svg>"""
    matching_svg = """<svg viewBox="0 0 100 100"><text>2x − 1 cm</text><text>x + 3 cm</text></svg>"""

    assert generator._diagram_missing_measurements(question, mismatched_svg) == ["2x - 1 cm"]
    assert generator._diagram_missing_measurements(question, matching_svg) == []


def test_degree_symbol_matches_degrees_measurement() -> None:
    question = "In triangle ABC, if angle BAC = 70 degrees and AB = 5 cm, find BC."
    svg = """<svg viewBox="0 0 100 100"><text>70°</text><text>5 cm</text></svg>"""

    assert generator._diagram_missing_measurements(question, svg) == []


def test_required_diagram_is_regenerated_when_initial_diagram_is_missing(monkeypatch) -> None:
    plan = [Slot(1, 6, "easy")]
    question = GeneratedQuestion(
        slot=1,
        question="In triangle ABC, if AB = 3 cm and BC = 4 cm, find AC.",
        solution="Working",
        final_answer="5 cm",
    )
    svg = '<svg viewBox="0 0 100 100"><text>3 cm</text><text>4 cm</text></svg>'

    def generate_batch(batch, phase, batch_number, avoid_questions=None):
        del batch, phase, batch_number, avoid_questions
        return {1: question}

    calls = []

    def generate_diagram(prompt, batch_number, **kwargs):
        del prompt, batch_number
        calls.append(kwargs)
        return svg, "A triangle with sides AB and BC labelled."

    monkeypatch.setattr(generator, "_generate_batch", generate_batch)
    monkeypatch.setattr(generator, "_generate_diagram", generate_diagram)

    result = asyncio.run(generator.generate_questions(plan))

    assert result[0].diagram_svg is not None
    assert result[0].diagram_alt == "A triangle with sides AB and BC labelled."
    assert calls[0]["attempts"] == generator.DIAGRAM_GENERATION_ATTEMPTS == 2


def test_diagram_review_checks_question_and_candidate_svg(monkeypatch) -> None:
    question = "In triangle ABC, AB = 3 cm and BC = 4 cm. Find AC."
    svg = '<svg viewBox="0 0 100 100"><text>3 cm</text></svg>'
    prompts = []

    def generate_content(**kwargs):
        prompts.append(kwargs["contents"])
        return SimpleNamespace(
            parsed=DiagramReview(
                faithful=False,
                issues=["The 3 cm label is attached to AC instead of AB."],
            )
        )

    monkeypatch.setattr(
        generator,
        "_client_instance",
        lambda: SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)),
    )

    assert generator._review_diagram(question, svg, "A labelled triangle.") == [
        "The 3 cm label is attached to AC instead of AB."
    ]
    assert question in prompts[0]
    assert svg in prompts[0]
    assert "actual geometry and SVG coordinates" in prompts[0]


def test_diagram_generation_uses_review_feedback_on_next_attempt(monkeypatch) -> None:
    question = "In triangle ABC, AB = 3 cm and BC = 4 cm. Find AC."
    candidates = [
        '<svg viewBox="0 0 100 100"><text>3 cm</text><text>4 cm</text></svg>',
        '<svg viewBox="0 0 100 100"><text>3 cm</text><text>4 cm</text></svg>',
    ]
    prompts = []

    def generate_content(**kwargs):
        prompts.append(kwargs["contents"])
        return SimpleNamespace(
            parsed=GeneratedDiagram(
                diagram_svg=candidates.pop(0),
                diagram_alt="A triangle with sides AB and BC labelled.",
            )
        )

    reviews = iter(
        [
            ["The 3 cm label is attached to AC instead of AB."],
            [],
        ]
    )
    monkeypatch.setattr(
        generator,
        "_client_instance",
        lambda: SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)),
    )

    def review_diagram(question, svg, alt):
        del question, svg, alt
        return next(reviews)

    monkeypatch.setattr(generator, "_review_diagram", review_diagram)

    svg, alt = generator._generate_diagram(question, 1, attempts=2)

    assert svg is not None
    assert alt == "A triangle with sides AB and BC labelled."
    assert len(prompts) == 2
    assert "attached to AC instead of AB" in prompts[1]


def test_diagram_generation_fails_after_two_rejected_candidates(monkeypatch) -> None:
    question = "In triangle ABC, AB = 3 cm and BC = 4 cm. Find AC."
    svg = '<svg viewBox="0 0 100 100"><text>3 cm</text><text>4 cm</text></svg>'
    calls = []

    def generate_content(**kwargs):
        calls.append(kwargs["contents"])
        return SimpleNamespace(
            parsed=GeneratedDiagram(
                diagram_svg=svg,
                diagram_alt="A triangle with sides AB and BC labelled.",
            )
        )

    monkeypatch.setattr(
        generator,
        "_client_instance",
        lambda: SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)),
    )
    def reject_diagram(question, candidate, alt):
        del question, candidate, alt
        return ["The diagram puts the given side length on the wrong side."]

    monkeypatch.setattr(generator, "_review_diagram", reject_diagram)

    with pytest.raises(RuntimeError, match="after 2 attempt\\(s\\)"):
        generator._generate_diagram(question, 1)

    assert len(calls) == generator.DIAGRAM_GENERATION_ATTEMPTS == 2


def test_invalid_argument_during_generation_is_not_retried(monkeypatch) -> None:
    calls = 0

    def reject_generation(**kwargs):
        nonlocal calls
        calls += 1
        del kwargs
        raise InvalidArgumentError("400 INVALID_ARGUMENT")

    monkeypatch.setattr(
        generator,
        "_client_instance",
        lambda: SimpleNamespace(models=SimpleNamespace(generate_content=reject_generation)),
    )

    with pytest.raises(
        RuntimeError,
        match="after 1 attempt.*rejected the diagram generation request",
    ):
        generator._generate_diagram(
            "In triangle ABC, AB = 3 cm. Find AC.",
            1,
            attempts=2,
        )

    assert calls == 1


def test_inconsistent_diagram_is_regenerated_from_final_question(monkeypatch) -> None:
    plan = [Slot(1, 6, "easy")]
    question = GeneratedQuestion(
        slot=1,
        question="In triangle ABC, if AB = 3 cm and BC = 4 cm, find AC.",
        solution="Working",
        final_answer="5 cm",
        diagram_svg='<svg viewBox="0 0 100 100"><text>30 cm</text><text>4 cm</text></svg>',
        diagram_alt="A triangle with sides labelled.",
    )
    regenerated_svg = '<svg viewBox="0 0 100 100"><text>3 cm</text><text>4 cm</text></svg>'

    def generate_batch(*args, **kwargs):
        del args, kwargs
        return {1: question}

    monkeypatch.setattr(generator, "_generate_batch", generate_batch)
    calls = []

    def generate_diagram(prompt, batch_number, **kwargs):
        calls.append((prompt, batch_number, kwargs))
        return regenerated_svg, "A triangle with sides AB and BC labelled."

    monkeypatch.setattr(generator, "_generate_diagram", generate_diagram)

    result = asyncio.run(generator.generate_questions(plan))

    assert len(calls) == 1
    assert question.question in calls[0][0]
    assert calls[0][2]["attempts"] == generator.DIAGRAM_GENERATION_ATTEMPTS - 1
    assert result[0].diagram_svg is not None
    assert "30 cm" not in result[0].diagram_svg
    assert "3 cm" in result[0].diagram_svg


def test_diagrams_are_processed_concurrently_within_configured_limit(monkeypatch) -> None:
    plan = [Slot(slot, 6, "easy") for slot in range(1, 5)]
    questions = {
        slot.slot: GeneratedQuestion(
            slot=slot.slot,
            question=f"In triangle ABC, AB = {slot.slot} cm. Find AC.",
            solution="Working",
            final_answer="Answer",
        )
        for slot in plan
    }
    active_calls = 0
    peak_calls = 0
    lock = Lock()
    monkeypatch.setattr(generator, "MAX_PARALLEL_CALLS", 2)

    def generate_batch(batch, _phase, _batch_number, _avoid_questions=None):
        del _phase, _batch_number, _avoid_questions
        return {slot.slot: questions[slot.slot] for slot in batch}

    monkeypatch.setattr(generator, "_generate_batch", generate_batch)

    def generate_diagram(question, batch_number, **kwargs):
        nonlocal active_calls, peak_calls
        del batch_number, kwargs
        with lock:
            active_calls += 1
            peak_calls = max(peak_calls, active_calls)
        time.sleep(0.02)
        with lock:
            active_calls -= 1
        return (
            '<svg viewBox="0 0 100 100"><text>1 cm</text><text>2 cm</text>'
            '<text>3 cm</text><text>4 cm</text></svg>',
            f"Diagram for {question}",
        )

    monkeypatch.setattr(generator, "_generate_diagram", generate_diagram)

    result = asyncio.run(generator.generate_questions(plan))

    assert peak_calls == 2
    assert [question.slot for question in result] == [1, 2, 3, 4]
