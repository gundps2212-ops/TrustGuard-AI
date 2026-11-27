"""Additional model providers used by TrustGuard's multi-model comparison."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

from modules.config import require_secret

load_dotenv()

GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "You are a factual educational assistant. Answer clearly, briefly and accurately. "
    "Do not invent information. Clearly mention uncertainty when necessary."
)


def _clean_question(question: str) -> str:
    clean = question.strip()
    if not clean:
        raise ValueError("Question cannot be empty.")
    return clean


def generate_llama_answer(question: str) -> str:
    """Generate an answer using Llama through Groq."""
    api_key = require_secret("GROQ_API_KEY")
    prompt = (
        "Answer the following question using simple, clear language. "
        "Include relevant facts, avoid invented details, and state uncertainty.\n\n"
        f"Question:\n{_clean_question(question)}"
    )
    try:
        response = Groq(api_key=api_key).chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=700,
        )
        answer = (response.choices[0].message.content or "").strip()
        if not answer:
            raise RuntimeError("Llama returned an empty response.")
        return answer
    except Exception as error:
        raise RuntimeError(f"Unable to generate the Llama answer: {error}") from error


def generate_openai_answer(question: str) -> str:
    """Generate an answer using OpenAI GPT (server-side API key only)."""
    api_key = require_secret("OPENAI_API_KEY")
    prompt = (
        "Answer the following question using simple, clear language. "
        "Include relevant facts, avoid invented details, and state uncertainty.\n\n"
        f"Question:\n{_clean_question(question)}"
    )
    try:
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=700,
        )
        answer = (response.choices[0].message.content or "").strip()
        if not answer:
            raise RuntimeError("OpenAI GPT returned an empty response.")
        return answer
    except Exception as error:
        raise RuntimeError(f"Unable to generate the OpenAI GPT answer: {error}") from error
