from __future__ import annotations

from supabase import Client, create_client

from modules.config import require_secret


# =========================================================
# NORMAL SUPABASE CLIENT
# =========================================================

def create_supabase_client() -> Client:
    """
    Create Supabase client using project URL
    and publishable key.
    """

    supabase_url = require_secret(
        "SUPABASE_URL"
    )

    supabase_key = require_secret(
        "SUPABASE_PUBLISHABLE_KEY"
    )

    return create_client(
        supabase_url,
        supabase_key,
    )


# =========================================================
# AUTHENTICATED SUPABASE CLIENT
# =========================================================

def create_authenticated_client(
    access_token: str,
    refresh_token: str,
) -> Client:
    """
    Create Supabase client and restore
    logged-in user's authentication session.
    """

    clean_access_token = str(
        access_token or ""
    ).strip()

    clean_refresh_token = str(
        refresh_token or ""
    ).strip()

    if not clean_access_token:
        raise ValueError(
            "Access token is required."
        )

    if not clean_refresh_token:
        raise ValueError(
            "Refresh token is required."
        )

    client = create_supabase_client()

    response = client.auth.set_session(
        clean_access_token,
        clean_refresh_token,
    )

    if response.session is None:
        raise RuntimeError(
            "Unable to restore Supabase session."
        )

    return client