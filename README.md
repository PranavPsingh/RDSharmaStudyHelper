# Class X Maths Study Helper

Generates 10 fresh practice questions from the NCERT Class X Mathematics textbook using Gemini.

- **Difficulty split:** 5 hard, 3 medium, 2 easy (worth 5 / 3 / 1 marks each)
- **Chapter weighting:** based on the CBSE theory paper (80 marks), plus a small token weight for the two optional appendices
- **Chapter picker:** dropdown for any of the 14 chapters or the 2 appendices, or "All chapters (random)", which samples in proportion to weightage (max 2 questions per chapter)
- **Print and answer access:** print all 10 generated questions, and unlock fully worked, step-by-step solutions with the answer password. Answer access expires after 30 minutes.

Stack: FastAPI + `google-genai` (backend), React + Vite (frontend).

## Setup

1. Put the textbook PDF at `backend/data/textbook.pdf`. Keep this repo private: the book is NCERT-copyrighted ("not to be republished").
2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
3. Find the page offset and put it in `.env` as `PDF_PAGE_OFFSET`:
   ```
   pip install -r backend/requirements.txt
   python backend/scripts/find_offset.py
   ```
   The printed page numbers in the book (Chapter 1 = page 1) differ from PDF page numbers because of the front matter.
4. Run the backend:
   ```
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```
5. Run the frontend:
   ```
   cd frontend
   npm install
   npm run dev
   ```
   Open http://localhost:5173.

## Gemini generation settings

- `EXCERPT_CHARS` sets the approximate number of textbook characters included per chapter excerpt (default `15000`). Excerpts sample across the chapter; questions may use any topic in that chapter.
- `MAX_PARALLEL_CALLS` sets the number of concurrent Gemini requests (default `3`). Lower this on the free Gemini tier if you see 429 rate-limit errors.
- `GEMINI_THINKING_BUDGET` sets Gemini's thinking budget (default `1024`). Set it to a blank value to omit the setting. A budget of `0` is fastest, but makes wrong answers more likely.
- Temporary Gemini `500`, `502`, `503`, and `504` service/network errors are retried with exponential backoff, up to five attempts per request. If 503 errors continue, wait and retry later or lower `MAX_PARALLEL_CALLS` to `1` in your environment settings to reduce simultaneous requests.

Generated diagrams are checked against measurements stated in their questions and reviewed by a
separate model call to verify that the figure corresponds to the question, including whether labels
and measurements belong to the correct parts. They do not need to be to scale. A rejected diagram
gets at most one redraw with the reviewer's feedback (two diagram candidates total). Diagram calls
do not override the model's thinking configuration and retry transient service errors at most once,
limiting extra usage. If Gemini rejects an optional review request, a diagram that passes SVG
sanitization and measurement checks is kept rather than failing generation. If a diagram still does
not correspond to a question that needs one, generation fails rather than returning a misleading
figure. Question batches and diagram checks run concurrently, with each stage capped at
`MAX_PARALLEL_CALLS` simultaneous tasks.

## Deploying on Vercel

1. Push this repository to GitHub as a **private** repository, with `backend/data/textbook.pdf` committed.
2. In Vercel, select **Add New -> Project**, import the repository, and leave **Root Directory** set to the repository root.
3. Under **Settings -> Build and Deployment -> Framework Preset**, select **Services**. Redeploy if the initial build ran before you changed this setting.
4. Under **Settings -> Environment Variables**, set `GEMINI_API_KEY` and `PDF_PAGE_OFFSET`. Optionally set `GEMINI_MODEL`, `MAX_PARALLEL_CALLS`, `GEMINI_THINKING_BUDGET`, and `EXCERPT_CHARS`.
5. Open `<url>/api/chapters` to verify the API, then generate a question set in the UI. Generation timing logs appear in Vercel runtime logs.

Troubleshooting:

- If the API returns `Textbook PDF not found`, the PDF was not bundled with the backend service. An unverified possible workaround is to add `"functions": { "app/main.py": { "includeFiles": "data/**" } }` inside the `backend` service in `vercel.json`.
- If Vercel rejects the `entrypoint`, remove that line from the `backend` service in `vercel.json` so it auto-detects `app/main.py`.
- The production URL is public by default, so anyone with it can use the Gemini API key's quota. Review Vercel Deployment Protection settings and set a quota or budget limit in Google AI Studio.

## How the weights work

CBSE publishes marks per **unit**, not per chapter. `backend/chapters.json` holds those unit marks and each unit's marks are split evenly between its chapters:

| Unit | Marks | Chapters |
|---|---|---|
| Number Systems | 6 | Real Numbers |
| Algebra | 20 | Polynomials, Pair of Linear Equations, Quadratic Equations, APs |
| Coordinate Geometry | 6 | Coordinate Geometry |
| Geometry | 15 | Triangles, Circles |
| Trigonometry | 12 | Intro to Trigonometry, Applications |
| Mensuration | 10 | Areas Related to Circles, Surface Areas and Volumes |
| Statistics & Probability | 11 | Statistics, Probability |
| Appendices (optional) | 2 | Proofs in Mathematics (A1), Mathematical Modelling (A2) |

The appendices are optional reading and are not in the CBSE paper, so their 2 marks are only a token weight (about 1.2% each) so they occasionally appear in random mode. Raise or lower that number in `chapters.json` to change how often they show up; weights are relative, so percentages always sum to 100.

Check the CBSE numbers against the current syllabus and edit `chapters.json` if they change.

## Tweaking

- Difficulty counts and marks: `backend/app/planner.py`
- Prompt to Gemini: `backend/app/generator.py`
- Model: `GEMINI_MODEL` in `.env`
