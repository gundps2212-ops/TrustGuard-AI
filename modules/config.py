
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import streamlit as st
from dotenv import load_dotenv


# Project root: TrustGuard-AI/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Explicitly load the project's .env file
load_dotenv(dotenv_path=ENV_FILE, override=False)


def get_secret(
    secret_name: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """
    Read a secret from Streamlit secrets first,
    then environment variables and the project .env file.
    """

    # Check Streamlit secrets
    try:
        value = st.secrets.get(secret_name)

        if value is not None:
            cleaned_value = str(value).strip()
            if cleaned_value:
                return cleaned_value
    except Exception:
        pass

    # Check environment variables
    environment_value = os.getenv(secret_name)

    if environment_value and environment_value.strip():
        return environment_value.strip()

    # Compatibility with alternative Supabase key names
    if secret_name == "SUPABASE_PUBLISHABLE_KEY":
        for alternative_name in (
            "SUPABASE_KEY",
            "SUPABASE_ANON_KEY",
        ):
            alternative_value = os.getenv(alternative_name)

            if alternative_value and alternative_value.strip():
                return alternative_value.strip()

    return default


def require_secret(secret_name: str) -> str:
    """
    Return a required configuration value or raise a clear error.
    """

    value = get_secret(secret_name)

    if not value:
        raise ValueError(
            f"{secret_name} was not configured. "
            f"Check the project .env file: {ENV_FILE}"
        )

    return value
