import os
from modules.config import require_secret

from dotenv import load_dotenv
from groq import Groq



load_dotenv()


GROQ_MODEL_NAME = os.getenv(
    "GROQ_MODEL_NAME",
    "llama-3.3-70b-versatile",
)


def generate_llama_answer(
    question: str,
) -> str:
    """
    Generate a factual answer using Llama through Groq API.

    Args:
        question: User question.

    Returns:
        Llama-generated answer.
    """

    clean_question = question.strip()

    if not clean_question:
        raise ValueError(
            "Question cannot be empty."
        )

   
    gemini_api_key = require_secret(
        "GEMINI_API_KEY"
    )

    tavily_api_key = require_secret(
        "TAVILY_API_KEY"
        )

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY was not found in the .env file."
        )

    system_prompt = (
        "You are a factual educational assistant. "
        "Answer clearly, briefly and accurately. "
        "Do not invent information. "
        "Clearly mention uncertainty when necessary."
    )

    user_prompt = f"""
Answer the following question.

Rules:
1. Use simple and clear language.
2. Include only relevant factual information.
3. Do not invent dates, names, numbers or events.
4. Mention uncertainty when the answer is unclear.
5. Keep the answer concise.
6. Do not add unnecessary headings.

Question:
{clean_question}
"""

    try:
        client = Groq(
            api_key=api_key
        )

        response = client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.2,
            max_completion_tokens=700,
        )

        if not response.choices:
            raise RuntimeError(
                "Groq returned no response choices."
            )

        answer = (
            response.choices[0].message.content
            or ""
        ).strip()

        if not answer:
            raise RuntimeError(
                "Llama returned an empty response."
            )

        return answer

    except Exception as error:
        raise RuntimeError(
            f"Unable to generate the Llama answer: {error}"
        ) from error