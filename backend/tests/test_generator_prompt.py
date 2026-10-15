from backend.app import generator
from backend.app.chapters import CHAPTERS
from backend.app.planner import Slot


def test_prompt_requires_complete_worked_solutions(monkeypatch) -> None:
    monkeypatch.setattr(generator, "chapter_excerpt", lambda chapter_id, phase=0.0: "Sample text")
    chapter_id = CHAPTERS[0].id

    prompt = " ".join(generator._build_prompt([Slot(1, chapter_id, "hard")]).split())

    assert "complete, easy-to-follow school-textbook worked solution" in prompt
    assert "do not skip algebra," in prompt
    assert "arithmetic, substitutions, or reasoning" in prompt
    assert 'Number the working as "Step 1:", "Step 2:", etc.' in prompt
    assert "progressively more detailed for 3- and 5-mark questions" in prompt
