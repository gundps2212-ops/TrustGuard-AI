from __future__ import annotations

import os
from typing import Optional

import streamlit as st
from dotenv import load_dotenv


load_dotenv()


def get_secret(
    secret_name: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """
    Read secret from Streamlit secrets first
    and .env/environment variables second.
    """

    try:
        if secret_name in st.secrets:
            value = st.secrets[
                secret_name
            ]

            if value is not None:
                return str(
                    value
                ).strip()

    except Exception:
        pass

    environment_value = os.getenv(
        secret_name
    )

    if environment_value:
        return environment_value.strip()

    return default


def require_secret(
    secret_name: str,
) -> str:
    """
    Return required configuration value.
    """

    value = get_secret(
        secret_name
    )

    if not value:
        raise ValueError(
            f"{secret_name} was not configured."
        )

    return value