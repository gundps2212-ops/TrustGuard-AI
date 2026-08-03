import os

from dotenv import load_dotenv
from google import genai


# Load variables from the .env file
load_dotenv()

MODEL_NAME = "gemini-3.5-flash-lite"


def generate_ai_answer(question: str) -> str:
    """
    Generate an answer using the Gemini API.

    Args:
        question: Question entered by the user.

    Returns:
        Gemini-generated answer.
    """

    clean_question = question.strip()

    if not clean_question:
        raise ValueError("Question cannot be empty.")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY was not found. "
            "Please add it to the .env file."
        )

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an educational AI assistant.

Answer the following question clearly and factually.
Use simple language.
Do not invent information.
If you are uncertain, clearly mention the uncertainty.

Question:
{clean_question}
"""

        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=prompt
        )

        answer = (interaction.output_text or "").strip()

        if not answer:
            raise RuntimeError("Gemini returned an empty response.")

        return answer

    except Exception as error:
        raise RuntimeError(
            f"Unable to generate the AI answer: {error}"
        ) from error