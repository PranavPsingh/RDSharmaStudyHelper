# Class X Maths Study Helper

Generates 10 fresh practice questions from the NCERT Class X Mathematics textbook using Gemini.

- **Difficulty split:** 5 hard, 3 medium, 2 easy (worth 5 / 3 / 1 marks each)
- **Chapter weighting:** based on the CBSE theory paper (80 marks), plus a small token weight for the two optional appendices
- **Chapter picker:** dropdown for any of the 14 chapters or the 2 appendices, or "All chapters (random)", which samples in proportion to weightage (max 2 questions per chapter)

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

## Deploying on Vercel

This repository is configured as one Vercel Services project: the `frontend` service is public
at `/`, and the `backend` service receives public `/api/*` requests. The frontend calls the API
through same-origin relative URLs, so no service binding is needed; bindings are for server-side
calls from one service to another.

1. Push the private repository to GitHub with `backend/data/textbook.pdf` committed.
2. In Vercel, create a project from the repository and keep the repository root as the project
   root. Vercel discovers each service root from `vercel.json`.
3. Set `GEMINI_API_KEY` and `PDF_PAGE_OFFSET` as Vercel environment variables. Set
   `GEMINI_MODEL` only if you want to override the default.
4. Deploy, then check `/api/chapters` and generate a set in the UI.

For local multi-service testing, use `vercel dev` from the repository root.

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
