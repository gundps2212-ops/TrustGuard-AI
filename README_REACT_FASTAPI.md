# TrustGuard AI — React + FastAPI Edition

This migration adds a React + TypeScript frontend and a FastAPI API while retaining the existing Python AI modules and Supabase project.

## Architecture
- `frontend/`: React, Vite, TypeScript, Recharts, Framer Motion and Lucide.
- `backend/main.py`: FastAPI endpoints.
- `modules/`: existing AI, retrieval, scoring, PDF and Supabase modules. These remain in place.
- Supabase remains the authentication provider and PostgreSQL report store. No database migration is required for this frontend/API migration.

## Run locally
1. Create a Python virtual environment at the repository root.
2. Install existing project dependencies: `pip install -r requirements.txt`.
3. Install API dependencies: `pip install -r backend/requirements.txt`.
4. Copy the existing root `.env.example` values into a root `.env` file (never commit secrets). Keep the existing Supabase URL and publishable key.
5. Set `CORS_ORIGINS=http://localhost:5173` in the root `.env`.
6. Start the API from the repository root: `uvicorn backend.main:app --reload --port 8000`.
7. In another terminal: `cd frontend && npm install && npm run dev`.
8. Open `http://localhost:5173`. API docs: `http://localhost:8000/docs`.

## API routes
- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/verify` — Gemini answer (or supplied answer), claim extraction, optional Tavily evidence, Gemini verification, optional NLI, Trust Score V2 and Supabase save.
- `POST /api/verify/pdf` — PDF-backed verification using the existing PDF reader and FAISS + BM25 hybrid retrieval.
- `GET /api/history` — authenticated Supabase verification history.

## Security notes
- The browser receives only the Supabase user's access and refresh tokens. Never expose a Supabase service-role key or AI provider keys in the frontend.
- API requests require the user's bearer access token and refresh token header; report access remains scoped by the existing Supabase authenticated client and RLS.
- The frontend stores the Supabase session in localStorage for this first migration. For production, prefer secure, httpOnly cookies and add rate limiting, request-size limits, HTTPS, and structured server-side logging.
- The dashboard trend chart currently displays clearly-labelled illustrative sample data; replace it with date-grouped history once the database query includes the required aggregation.
- PDF verification is an API endpoint; wire a drag-and-drop uploader into the UI as a follow-up.
