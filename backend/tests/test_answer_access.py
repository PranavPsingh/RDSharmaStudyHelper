import asyncio

import pytest
from fastapi import HTTPException

from backend.app import main
from backend.app.chapters import CHAPTERS
from backend.app.schemas import AnswersRequest, GenerateRequest, QuestionOut


def _question(slot: int, solution: str, final_answer: str) -> QuestionOut:
    chapter = CHAPTERS[0]
    return QuestionOut(
        slot=slot,
        chapter_id=chapter.id,
        chapter_label=chapter.label,
        chapter_title=chapter.title,
        chapter_weight_pct=chapter.weight_pct,
        difficulty="easy",
        marks=1,
        question=f"Question {slot}?",
        solution=solution,
        final_answer=final_answer,
    )


def test_answers_are_withheld_until_password_is_verified(monkeypatch) -> None:
    questions = [
        _question(1, "Working 1", "Answer 1"),
        _question(2, "Working 2", "Answer 2"),
    ]
    def build_plan(chapter_id):
        del chapter_id
        return []

    monkeypatch.setattr(main, "build_plan", build_plan)
    async def generate_questions(plan):
        del plan
        return questions

    monkeypatch.setattr(main, "generate_questions", generate_questions)

    generated = asyncio.run(main.generate(GenerateRequest()))

    assert len(generated.questions) == 2
    assert "solution" not in generated.questions[0].model_dump()
    assert "final_answer" not in generated.questions[0].model_dump()

    with pytest.raises(HTTPException) as error:
        main.get_answers(
            AnswersRequest(answer_token=generated.answer_token, password="incorrect")
        )
    assert error.value.status_code == 401

    response = main.get_answers(
        AnswersRequest(
            answer_token=generated.answer_token,
            password="PranayRaj@2005",
        )
    )
    assert [answer.final_answer for answer in response.answers] == ["Answer 1", "Answer 2"]


def test_answers_reject_unknown_question_set() -> None:
    with pytest.raises(HTTPException) as error:
        main.get_answers(AnswersRequest(answer_token="unknown", password="PranayRaj@2005"))
    assert error.value.status_code == 404
