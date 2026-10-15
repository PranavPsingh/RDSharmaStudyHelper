import { useEffect, useState } from "react";
import { fetchChapters, generateQuestions } from "./api.js";

const ALL = "all";

function QuestionCard({ q }) {
  const [open, setOpen] = useState(false);
  return (
    <li className={`card ${q.difficulty}`}>
      <div className="card-head">
        <span className={`badge ${q.difficulty}`}>{q.difficulty}</span>
        <span className="meta">
          {q.chapter_label}: {q.chapter_title} · {q.marks} mark{q.marks > 1 ? "s" : ""}
        </span>
      </div>
      <p className="question">
        {q.slot}. {q.question}
      </p>
      <button className="link" onClick={() => setOpen(!open)}>
        {open ? "Hide answer" : "Show answer"}
      </button>
      {open && (
        <div className="answer">
          <pre>{q.solution}</pre>
          <p>
            <strong>Answer:</strong> {q.final_answer}
          </p>
        </div>
      )}
    </li>
  );
}

export default function App() {
  const [chapters, setChapters] = useState([]);
  const [selected, setSelected] = useState(ALL);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchChapters().then(setChapters).catch((e) => setError(e.message));
  }, []);

  async function onGenerate() {
    setLoading(true);
    setError("");
    try {
      const chapterId = selected === ALL ? null : Number(selected);
      setResult(await generateQuestions(chapterId));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Class X Maths Practice</h1>

      <div className="controls">
        <label htmlFor="chapter">Chapter</label>
        <select id="chapter" value={selected} onChange={(e) => setSelected(e.target.value)}>
          <option value={ALL}>All chapters (random)</option>
          {chapters.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}: {c.title}
            </option>
          ))}
        </select>
        <button onClick={onGenerate} disabled={loading}>
          {loading ? "Generating…" : "Generate 10 questions"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <p className="summary">
            {result.questions.length} questions · {result.total_marks} marks total
          </p>
          <ol className="questions">
            {result.questions.map((q) => (
              <QuestionCard key={q.slot} q={q} />
            ))}
          </ol>
        </>
      )}
    </main>
  );
}
