from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

from modules.auth_manager import authenticate_user, register_user
from modules.claim_extractor import extract_factual_claims
from modules.database_manager import get_verification_history, save_verification
from modules.llm import generate_ai_answer
from modules.nli_detector import analyze_evidence_nli
from modules.pdf_reader import extract_multiple_pdfs
from modules.score import count_statuses, get_trust_level
from modules.trust_score_v2 import calculate_trust_score_v2
from modules.supabase_manager import create_authenticated_client
from modules.verifier import verify_all_claims
from modules.web_retriever import TRUSTED_DOMAIN_GROUPS, search_web_evidence

app = FastAPI(
    title="TrustGuard AI API",
    version="2.0.0",
    description="React + FastAPI API for the existing TrustGuard AI verification engine.",
)

origins = [
    item.strip()
    for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterPayload(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: str
    password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)


class LoginPayload(BaseModel):
    email: str
    password: str


class VerifyPayload(BaseModel):
    question: str = Field(min_length=3, max_length=5000)
    answer: str | None = None
    use_web: bool = True
    compare_llama: bool = False
    domain_group: str = "No domain filter"
    minimum_relevance: float = Field(default=0.35, ge=0, le=1)
    run_nli: bool = False


def get_session(
    authorization: str | None = Header(default=None),
    x_refresh_token: str | None = Header(default=None),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    access_token = authorization.split(" ", 1)[1].strip()
    if not access_token or not x_refresh_token:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    try:
        client = create_authenticated_client(access_token, x_refresh_token)
        user_response = client.auth.get_user()
        user = user_response.user
        if user is None:
            raise ValueError("No authenticated user returned.")
        return {
            "client": client,
            "user_id": str(user.id),
            "email": user.email or "",
            "access_token": access_token,
            "refresh_token": x_refresh_token,
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired Supabase session.")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "TrustGuard AI API", "version": "2.0.0"}


@app.post("/api/auth/register")
def register(payload: RegisterPayload):
    success, message = register_user(
        payload.username, payload.email, payload.password, payload.confirm_password
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


@app.post("/api/auth/login")
def login(payload: LoginPayload):
    session = authenticate_user(payload.email, payload.password)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid email or password, or email confirmation is pending.")
    return {
        "user": {
            "id": session["id"],
            "username": session["username"],
            "email": session["email"],
            "role": session["role"],
        },
        "session": {
            "access_token": session["access_token"],
            "refresh_token": session["refresh_token"],
        },
    }


@app.get("/api/auth/me")
def me(session: dict[str, Any] = Depends(get_session)):
    profile_response = (
        session["client"].table("profiles")
        .select("username, role, created_at")
        .eq("id", session["user_id"]).limit(1).execute()
    )
    profile = profile_response.data[0] if profile_response.data else {}
    return {
        "id": session["user_id"],
        "email": session["email"],
        "username": profile.get("username", "User"),
        "role": profile.get("role", "user"),
    }


@app.post("/api/verify")
def verify(payload: VerifyPayload, session: dict[str, Any] = Depends(get_session)):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Enter a question to verify.")

    try:
        answer = payload.answer.strip() if payload.answer else generate_ai_answer(question)
        if not answer:
            raise ValueError("The AI answer is empty.")

        claims = extract_factual_claims(answer)
        if not claims:
            raise ValueError("No factual claims could be extracted from this answer.")

        claim_items = []
        for claim in claims[:10]:
            evidence = []
            if payload.use_web:
                evidence = search_web_evidence(
                    claim,
                    max_results=5,
                    domain_group=payload.domain_group if payload.domain_group in TRUSTED_DOMAIN_GROUPS else "No domain filter",
                    minimum_score=payload.minimum_relevance,
                )
            claim_items.append({"claim": claim, "evidence": evidence})

        results = verify_all_claims(claim_items)
        for index, result in enumerate(results):
            result["claim"] = claim_items[index]["claim"]
            result["evidence"] = claim_items[index]["evidence"]
            if payload.run_nli and result["evidence"]:
                result["evidence"] = analyze_evidence_nli(
                    result["claim"], result["evidence"]
                )

        metrics = calculate_trust_score_v2(results)
        score = round(float(metrics.get("final_score", 0)))
        statuses = count_statuses(results)
        report = {
            "question": question,
            "original_ai_answer": answer,
            "final_verified_response": answer,
            "verification_results": results,
            "overall_trust_score": score,
            "trust_level": get_trust_level(score),
            "trust_metrics": metrics,
            "status_counts": statuses,
            "document_name": "Web evidence" if payload.use_web else "No document",
        }

        saved_id = save_verification(
            report_data=report,
            user_id=session["user_id"],
            access_token=session["access_token"],
            refresh_token=session["refresh_token"],
        )
        return {"id": saved_id, **report}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Verification failed: {error}")


@app.post("/api/verify/pdf")
async def verify_pdf(
    question: str = Form(...),
    files: list[UploadFile] = File(...),
    run_nli: bool = Form(False),
    session: dict[str, Any] = Depends(get_session),
):
    if not question.strip():
        raise HTTPException(status_code=400, detail="Enter a question to verify.")
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one PDF.")
    try:
        import io
        uploaded = []
        for item in files:
            filename = item.filename or "uploaded_document.pdf"
            if item.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f"{filename} is not a PDF.")
            raw = await item.read()
            if len(raw) > 15 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Each PDF must be 15 MB or smaller.")
            stream = io.BytesIO(raw)
            stream.name = filename
            uploaded.append(stream)
        # Reuse the existing PDF reader without changing its interface.
        page_records, page_count = extract_multiple_pdfs(uploaded)
        from modules.evidence_retriever import build_evidence_index, search_evidence
        chunks, index = build_evidence_index(page_records)
        answer = generate_ai_answer(question.strip())
        claims = extract_factual_claims(answer)
        claim_items = []
        for claim in claims[:10]:
            evidence = search_evidence(claim, chunks, index, top_k=5) if index else []
            claim_items.append({"claim": claim, "evidence": evidence})
        results = verify_all_claims(claim_items)
        for i, result in enumerate(results):
            result["claim"] = claim_items[i]["claim"]
            result["evidence"] = claim_items[i]["evidence"]
            if run_nli and result["evidence"]:
                result["evidence"] = analyze_evidence_nli(result["claim"], result["evidence"])
        metrics = calculate_trust_score_v2(results)
        score = round(float(metrics.get("final_score", 0)))
        report = {
            "question": question.strip(),
            "original_ai_answer": answer,
            "final_verified_response": answer,
            "verification_results": results,
            "overall_trust_score": score,
            "trust_level": get_trust_level(score),
            "trust_metrics": metrics,
            "status_counts": count_statuses(results),
            "document_name": ", ".join(item.name for item in uploaded),
            "total_pages": page_count,
        }
        saved_id = save_verification(report, session["user_id"], session["access_token"], session["refresh_token"])
        return {"id": saved_id, **report}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"PDF verification failed: {error}")


@app.get("/api/history")
def history(limit: int = 50, session: dict[str, Any] = Depends(get_session)):
    try:
        records = get_verification_history(
            session["user_id"], session["access_token"], session["refresh_token"], limit
        )
        return {"items": records}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unable to load history: {error}")
