import { useEffect, useState } from "react";
import { fetchAnswers, fetchChapters, generateQuestions } from "./api.js";

const ALL = "all";

function QuestionCard({ q, answer, unlocked, onUnlock }) {
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  async function submitPassword(event) {
    event.preventDefault();
    setError("");
    try {
      await onUnlock(password);
      setPassword("");
      setShowPassword(false);
    } catch (e) {
      setError(e.message);
    }
  }

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
      {q.diagram_svg && (
        <figure className="diagram">
          <img
            src={`data:image/svg+xml;utf8,${encodeURIComponent(q.diagram_svg)}`}
            alt={q.diagram_alt || "Diagram for the question"}
          />
        </figure>
      )}
      {!unlocked && (
        <>
          <button className="link answer-control" onClick={() => setShowPassword(!showPassword)}>
            {showPassword ? "Cancel" : "Show answer"}
          </button>
          {showPassword && (
            <form className="answer-control password-form" onSubmit={submitPassword}>
              <label htmlFor={`answer-password-${q.slot}`}>Enter password to unlock all answers</label>
              <input
                id={`answer-password-${q.slot}`}
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
              <button type="submit">Unlock answers</button>
              {error && <p className="error">{error}</p>}
            </form>
          )}
        </>
      )}
      {unlocked && answer && (
        <div className="answer">
          <pre>{answer.solution}</pre>
          <p>
            <strong>Answer:</strong> {answer.final_answer}
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
  const [answers, setAnswers] = useState(null);

  useEffect(() => {
    fetchChapters().then(setChapters).catch((e) => setError(e.message));
  }, []);

  async function onGenerate() {
    setLoading(true);
    setError("");
    try {
      const chapterId = selected === ALL ? null : Number(selected);
      setResult(await generateQuestions(chapterId));
      setAnswers(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onUnlock(password) {
    const response = await fetchAnswers(result.answer_token, password);
    setAnswers(Object.fromEntries(response.answers.map((answer) => [answer.slot, answer])));
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
          <div className="result-actions">
            <p className="summary">
              {result.questions.length} questions · {result.total_marks} marks total
            </p>
            <button className="print-button" onClick={() => window.print()}>
              Print questions
            </button>
          </div>
          <ol className="questions">
            {result.questions.map((q) => (
              <QuestionCard
                key={q.slot}
                q={q}
                answer={answers?.[q.slot]}
                unlocked={Boolean(answers)}
                onUnlock={onUnlock}
              />
            ))}
          </ol>
        </>
      )}
    </main>
  );
}
