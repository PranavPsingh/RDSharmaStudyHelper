import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "chapters.json"


@dataclass(frozen=True)
class Chapter:
    id: int
    title: str
    start_page: int  # printed page number in the book
    end_page: int
    unit: str
    weight_pct: float  # relative weight across all entries (sums to ~100)
    label: str  # "Ch 1", "Appendix A1", ...


def _load() -> list[Chapter]:
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    chapters = raw["chapters"]
    unit_marks = raw["unit_marks"]
    # The 80 CBSE theory marks plus a small token weight for the optional appendices,
    # so the appendices can show up in random mode without dominating it.
    total = sum(unit_marks.values())
    per_unit = Counter(c["unit"] for c in chapters)

    result = []
    for i, c in enumerate(chapters):
        end = chapters[i + 1]["start_page"] - 1 if i + 1 < len(chapters) else raw["last_page"]
        # CBSE publishes marks per unit, not per chapter, so a unit's marks
        # are split evenly across its chapters. Tweak chapters.json to change this.
        weight = unit_marks[c["unit"]] / per_unit[c["unit"]] / total * 100
        result.append(
            Chapter(
                id=c["id"],
                title=c["title"],
                start_page=c["start_page"],
                end_page=end,
                unit=c["unit"],
                weight_pct=round(weight, 2),
                label=c.get("label", f"Ch {c['id']}"),
            )
        )
    return result


CHAPTERS = _load()
BY_ID = {c.id: c for c in CHAPTERS}
