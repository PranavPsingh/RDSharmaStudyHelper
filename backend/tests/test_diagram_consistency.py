from backend.app import generator
from backend.app.planner import Slot
from backend.app.schemas import GeneratedQuestion


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

    def generate_diagram(prompt, batch_number):
        del prompt, batch_number
        return svg, "A triangle with sides AB and BC labelled."

    monkeypatch.setattr(generator, "_generate_batch", generate_batch)
    monkeypatch.setattr(generator, "_generate_diagram", generate_diagram)

    result = generator.generate_questions(plan)

    assert result[0].diagram_svg is not None
    assert result[0].diagram_alt == "A triangle with sides AB and BC labelled."


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

    def generate_diagram(prompt, batch_number):
        calls.append((prompt, batch_number))
        return regenerated_svg, "A triangle with sides AB and BC labelled."

    monkeypatch.setattr(generator, "_generate_diagram", generate_diagram)

    result = generator.generate_questions(plan)

    assert len(calls) == 1
    assert question.question in calls[0][0]
    assert result[0].diagram_svg is not None
    assert "30 cm" not in result[0].diagram_svg
    assert "3 cm" in result[0].diagram_svg
