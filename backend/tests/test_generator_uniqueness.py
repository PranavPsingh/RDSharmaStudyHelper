import asyncio

import pytest

from backend.app import generator
from backend.app.planner import Slot
from backend.app.schemas import GeneratedQuestion


def _question(slot: int, text: str) -> GeneratedQuestion:
    return GeneratedQuestion(
        slot=slot,
        question=text,
        solution="Working",
        final_answer="Answer",
    )


def test_generate_questions_regenerates_duplicate_text_across_batches(monkeypatch) -> None:
    plan = [
        Slot(1, 6, "easy"),
        Slot(2, 6, "easy"),
        Slot(3, 6, "medium"),
        Slot(4, 6, "hard"),
    ]
    monkeypatch.setattr(generator, "MAX_PARALLEL_CALLS", 2)
    regeneration_avoid_lists: list[list[str] | None] = []

    def generate_batch(batch, phase, batch_number, avoid_questions=None):
        del phase, batch_number
        if len(batch) == 1:
            regeneration_avoid_lists.append(avoid_questions)
            return {batch[0].slot: _question(batch[0].slot, "A different question?")}

        return {
            1: _question(1, "Find the value of x."),
            2: _question(2, "  Find   the value of X. "),
            3: _question(3, "Calculate the area of a square."),
            4: _question(4, "Solve the quadratic equation."),
        }

    monkeypatch.setattr(generator, "_generate_batch", generate_batch)

    result = asyncio.run(generator.generate_questions(plan))

    assert [question.slot for question in result] == [1, 2, 3, 4]
    assert len({generator._question_key(question.question) for question in result}) == 4
    assert regeneration_avoid_lists == [
        ["Find the value of x.", "Calculate the area of a square.", "Solve the quadratic equation."]
    ]


def test_generate_questions_fails_instead_of_returning_duplicates(monkeypatch) -> None:
    plan = [Slot(1, 6, "easy"), Slot(2, 6, "easy")]
    monkeypatch.setattr(generator, "MAX_PARALLEL_CALLS", 1)

    def generate_batch(batch, phase, batch_number, avoid_questions=None):
        del phase, batch_number, avoid_questions
        return {
            slot.slot: _question(slot.slot, "Repeated question?")
            for slot in batch
        }

    monkeypatch.setattr(generator, "_generate_batch", generate_batch)

    with pytest.raises(RuntimeError, match="repeated questions"):
        asyncio.run(generator.generate_questions(plan))
