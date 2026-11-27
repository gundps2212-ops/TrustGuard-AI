# TrustGuard AI — Hallucination Detection & Fact Verification

TrustGuard AI verifies factual claims in AI-generated answers using evidence retrieval, NLI and transparent trust scoring.

## Technology
- **Frontend:** React, TypeScript, Vite, Recharts, Framer Motion and Lucide.
- **API:** FastAPI.
- **AI engine:** Existing Gemini modules plus Llama through Groq and OpenAI GPT, with claim extraction, Tavily evidence retrieval, FAISS + BM25, Cross-Encoder, NLI, source reliability and Trust Score V2.
- **Database and authentication:** Existing Supabase project (Supabase Auth, PostgreSQL, Row Level Security).

## Run locally
Run commands from the repository root unless stated otherwise.

1. Create and activate a Python virtual environment.
2. Install the original engine dependencies: `pip install -r requirements.txt`.
3. Install API dependencies: `pip install -r backend/requirements.txt`.
4. Configure the existing Supabase and AI provider credentials in the root `.env` file: `GEMINI_API_KEY`, `GROQ_API_KEY`, and `OPENAI_API_KEY` (plus Supabase and Tavily). Optional model names: `GROQ_MODEL_NAME` and `OPENAI_MODEL_NAME` (default `gpt-4o-mini`). Use `.env.example` as a reference. Never commit secrets.
5. Add `CORS_ORIGINS=http://localhost:5173` to the root `.env`.
6. Start the API: `uvicorn backend.main:app --reload --port 8000`.
7. In a second terminal run `cd frontend && npm install && npm run dev`.
8. Open `http://localhost:5173`. API documentation is at `http://localhost:8000/docs`.

## API endpoints
- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/verify` — Gemini answer generation (or pasted answer), optional side-by-side Gemini + Llama + OpenAI GPT comparison, factual claim extraction, optional web evidence, verification, optional NLI, trust scoring and Supabase persistence.
- `POST /api/verify/pdf` — PDF text extraction and FAISS + BM25 evidence retrieval using the existing modules.
- `GET /api/history` — authenticated report history.

## Important notes
- Existing `modules/` and Supabase integration are retained. No schema or database replacement is included.
- The React app uses Supabase user access/refresh tokens to call the API. AI provider keys remain server-side; OpenAI GPT uses `OPENAI_API_KEY` and defaults to `gpt-4o-mini`. The three-model comparison is enabled by default in the verification workspace and can be switched off. The service-role key and AI provider keys must remain server-side.
- The frontend stores the auth session in localStorage for this initial implementation. For production deployment, move session handling to secure httpOnly cookies and add rate limiting, HTTPS, upload quotas and monitoring.
- PDF upload accepts PDF files up to 15 MB each.
- The overview chart currently labels its sample trend as illustrative; it is not presented as actual historical account analytics.
- The original Streamlit app remains in the repository as a legacy/fallback interface. Start the new React experience using the commands above.
