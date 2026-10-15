import random
from dataclasses import dataclass

from .chapters import CHAPTERS

# Order matters: this is the order questions are shown (easy -> hard).
DIFFICULTY_COUNTS = {"easy": 2, "medium": 3, "hard": 5}

# Marks a question of each difficulty is worth (CBSE style: 1 / 3 / 5 mark questions).
MARKS = {"easy": 1, "medium": 3, "hard": 5}

# In "all chapters" mode, no chapter gets more than this many of the 10 questions.
MAX_PER_CHAPTER = 2


@dataclass
class Slot:
    slot: int
    chapter_id: int
    difficulty: str


def build_plan(chapter_id: int | None, rng: random.Random | None = None) -> list[Slot]:
    """Decide which chapter and difficulty each of the 10 questions covers."""
    rng = rng or random.Random()
    difficulties = [d for d, n in DIFFICULTY_COUNTS.items() for _ in range(n)]

    if chapter_id is not None:
        chosen = [chapter_id] * len(difficulties)
    else:
        chosen: list[int] = []
        for _ in difficulties:
            pool = [c for c in CHAPTERS if chosen.count(c.id) < MAX_PER_CHAPTER]
            picked = rng.choices(pool, weights=[c.weight_pct for c in pool], k=1)[0]
            chosen.append(picked.id)

    return [Slot(i + 1, cid, d) for i, (cid, d) in enumerate(zip(chosen, difficulties))]
