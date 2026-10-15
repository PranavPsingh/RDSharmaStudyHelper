from pydantic import BaseModel


class GeneratedQuestion(BaseModel):
    slot: int
    question: str
    solution: str
    final_answer: str


class GeneratedSet(BaseModel):
    questions: list[GeneratedQuestion]


class GenerateRequest(BaseModel):
    # None means "all chapters, picked at random by CBSE weightage".
    chapter_id: int | None = None


class QuestionOut(BaseModel):
    slot: int
    chapter_id: int
    chapter_label: str
    chapter_title: str
    chapter_weight_pct: float
    difficulty: str
    marks: int
    question: str
    solution: str
    final_answer: str


class GenerateResponse(BaseModel):
    mode: str
    total_marks: int
    questions: list[QuestionOut]
