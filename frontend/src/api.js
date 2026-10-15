export async function fetchChapters() {
  const res = await fetch("/api/chapters");
  if (!res.ok) throw new Error("Could not load chapters");
  return res.json();
}

// chapterId = null means "all chapters, random by CBSE weightage"
export async function generateQuestions(chapterId) {
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chapter_id: chapterId }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Could not generate questions");
  }
  return res.json();
}

export async function fetchAnswers(answerToken, password) {
  const res = await fetch("/api/answers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer_token: answerToken, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Could not unlock answers");
  }
  return res.json();
}
