from pydantic import BaseModel


class GeneratedQuestion(BaseModel):
    slot: int
    question: str
    solution: str
    final_answer: str
    diagram_svg: str | None = None
    diagram_alt: str | None = None


class GeneratedSet(BaseModel):
    questions: list[GeneratedQuestion]


class GeneratedDiagram(BaseModel):
    diagram_svg: str | None = None
    diagram_alt: str | None = None


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
    diagram_svg: str | None = None
    diagram_alt: str | None = None


class PublicQuestion(BaseModel):
    slot: int
    chapter_id: int
    chapter_label: str
    chapter_title: str
    chapter_weight_pct: float
    difficulty: str
    marks: int
    question: str
    diagram_svg: str | None = None
    diagram_alt: str | None = None


class GenerateResponse(BaseModel):
    mode: str
    total_marks: int
    answer_token: str
    questions: list[PublicQuestion]


class AnswersRequest(BaseModel):
    answer_token: str
    password: str


class QuestionAnswer(BaseModel):
    slot: int
    solution: str
    final_answer: str


class AnswersResponse(BaseModel):
    answers: list[QuestionAnswer]
