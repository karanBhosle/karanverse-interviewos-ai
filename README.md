# InterviewOS AI

Personal interview and career intelligence coach for KaranVerse. The product combines resume intelligence, adaptive mock interviews, explainable rubric scoring, optional OpenCV visual presentation feedback, skill-gap tracking, and a learning roadmap.

This is not a generic chatbot with a dashboard around it, and it is not a hiring predictor.

## What the candidate can do

1. Upload a PDF or DOCX resume.
2. Paste a target job description.
3. Review extracted skills, projects, and achievements with source locations.
4. Compare documented resume evidence against job requirements.
5. Generate a personalized interview plan.
6. Complete a text or optional webcam-assisted mock interview.
7. Receive bounded adaptive follow-up questions.
8. See question-specific rubric scores computed in Python.
9. Review evidence excerpts, missing concepts, and skill gaps.
10. Generate and reassess a learning plan.
11. Track session history.
12. Delete resumes, sessions, and optional media.

## Evidence categories

The UI and API keep these separate:

| Category | Meaning |
| --- | --- |
| Resume facts | Text extracted from an uploaded file, with section/page when available |
| Job requirements | Inferred from the job description |
| Candidate answers | Typed or transcribed responses |
| Deterministic measurements | Concept coverage, weighted scores, visual geometry, filler counts |
| LLM interpretations | Optional analysis from a configured OpenAI-compatible API, never an unchecked final score |
| Validated evaluation results | Schema-checked dimension scores plus Python-computed weights |

A skill name on a resume is **keyword presence**, not demonstrated mastery.

## Architecture

```
frontend/   Next.js App Router, TypeScript, Tailwind, shadcn/ui, TanStack Query
backend/    FastAPI, SQLAlchemy 2, Alembic, LangGraph, OpenCV, hybrid RAG
infra/      Compose notes and architecture
scripts/    Local helpers
```

The LLM client is generic and OpenAI-compatible. Point `LLM_BASE_URL` at OpenAI, Azure, Groq, OpenRouter, Ollama, vLLM, or any `/chat/completions` server. Credentials stay on the Python backend. The frontend never receives an API key.

When no LLM API is configured, interviews still run against the curated question bank. Evaluations are labeled `deterministic_concept_coverage`. The API does not fabricate a successful LLM evaluation.

## Local setup

```bash
cp .env.example .env
# set AUTHENTICATION_SECRET to a long random value
# optionally set LLM_API_KEY, LLM_MODEL, and LLM_BASE_URL
```

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Health: `GET /api/v1/health`  
Ready: `GET /api/v1/ready`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Services: Next.js `:3000`, FastAPI `:8000`, PostgreSQL `:5432`, Redis `:6379`, Celery worker, Celery beat.

Migrations:

```bash
cd backend
alembic upgrade head
```

In development the API also creates tables on startup.

## Testing

```bash
cd backend
pip install -e ".[dev]"
pytest -q

cd ../frontend
node --test tests/visual.test.ts
```

Coverage includes resume parsing, job matching, adaptive follow-ups, rubric weight math, LLM provider failure handling, visual quality flags, ownership checks, and data deletion.

## Visual presentation feedback

Optional and independently disableable.

Allowed observations: face visibility, out-of-frame intervals, head-orientation variation, recording brightness/blur, insufficient data.

Not allowed: emotion, nervousness, honesty, personality, or “attention” labels.

Insufficient data is marked unavailable. Camera hardware, lighting, disabilities, cultural communication style, and permission denial are never converted into a poor technical score.

Head-orientation and gaze values are geometric proxies from a face box or landmarks. They are not validated attention or deception measures.

## Privacy

- Backend-only LLM API credentials
- JWT auth and per-user ownership checks
- Upload type and size limits
- Uploaded files are stored, never executed
- CORS allow-list
- Secret redaction in logs
- Raw video is not stored by default
- `DELETE /api/v1/users/me/data` removes resumes, sessions, media, and derived indexes

If resume or answer text is sent to an LLM provider, review that provider’s retention terms before enabling the key.

## Environment

See `.env.example` for `DATABASE_URL`, `REDIS_URL`, `LLM_*`, `EMBEDDING_MODEL`, `VECTOR_STORE_PATH`, `CORS_ORIGINS`, `AUTHENTICATION_SECRET`, `UPLOAD_LIMIT_MB`, `MEDIA_RETENTION_DAYS`, and `VISUAL_ANALYSIS_ENABLED`.

Never commit secrets.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Frontend cannot reach API | `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` |
| Resume upload rejected | PDF/DOCX only, default 8 MB limit |
| Scanned PDF has no text | Optional OCR extras are not installed by default |
| Evaluations say deterministic only | `LLM_API_KEY` is empty or the provider failed |
| Camera denied | Interview continues in text-only mode |
| Ready check degraded | PostgreSQL or Redis is down |

## Limitations

Scores are coaching signals. They are not validated predictors of job performance and must not be used to rank candidates for employers.
