import json
import os
import re

from dotenv import load_dotenv
from google import genai


load_dotenv()

MODEL_NAME = "gemini-3.5-flash-lite"


def clean_json_response(response_text: str) -> str:
    """
    Remove markdown formatting from Gemini JSON response.
    """

    cleaned_text = response_text.strip()

    cleaned_text = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned_text,
        flags=re.IGNORECASE
    )

    cleaned_text = re.sub(
        r"\s*```$",
        "",
        cleaned_text
    )

    # JSON array शोधणे
    start_index = cleaned_text.find("[")
    end_index = cleaned_text.rfind("]")

    if start_index == -1 or end_index == -1:
        raise ValueError(
            "Gemini did not return a valid JSON list."
        )

    return cleaned_text[start_index:end_index + 1]


def extract_factual_claims(ai_answer: str) -> list[str]:
    """
    Extract factual and verifiable claims from an AI-generated answer.
    """

    clean_answer = ai_answer.strip()

    if not clean_answer:
        raise ValueError("AI answer cannot be empty.")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY was not found in the .env file."
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a factual claim extraction system.

Extract only factual and externally verifiable statements
from the AI-generated answer below.

Rules:
1. Return only a JSON array of strings.
2. Each claim must contain one clear fact.
3. Do not include opinions, advice, greetings or headings.
4. Split combined factual sentences into separate claims.
5. Do not add information that is not present in the answer.
6. Return a maximum of 10 claims.

Example output:
[
  "India became independent on August 15, 1947.",
  "British rule in India ended in 1947."
]

AI-generated answer:
{clean_answer}
"""

    try:
        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=prompt
        )

        response_text = (
            interaction.output_text or ""
        ).strip()

        if not response_text:
            raise RuntimeError(
                "Gemini returned an empty claim extraction response."
            )

        json_text = clean_json_response(response_text)
        claims = json.loads(json_text)

        if not isinstance(claims, list):
            raise ValueError(
                "Extracted claims are not in list format."
            )

        valid_claims = []

        for claim in claims:
            if isinstance(claim, str) and claim.strip():
                valid_claims.append(claim.strip())

        return valid_claims

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Unable to understand the extracted claims."
        ) from error

    except Exception as error:
        raise RuntimeError(
            f"Claim extraction failed: {error}"
        ) from error