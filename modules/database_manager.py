from __future__ import annotations

from typing import Any

from modules.supabase_manager import (
    create_authenticated_client,
)


# =========================================================
# COMPATIBILITY FUNCTION
# =========================================================

def init_database() -> None:
    """
    Database tables are now managed by Supabase.

    This function is kept temporarily so that older
    pages importing init_database() do not crash.
    """

    return None


# =========================================================
# HELPERS
# =========================================================

def validate_user_id(
    user_id: Any,
) -> str:
    """
    Validate Supabase UUID user ID.
    """

    clean_user_id = str(
        user_id or ""
    ).strip()

    if not clean_user_id:
        raise ValueError(
            "A valid logged-in user ID is required."
        )

    return clean_user_id


def validate_tokens(
    access_token: str,
    refresh_token: str,
) -> tuple[str, str]:
    """
    Validate authentication tokens.
    """

    clean_access_token = str(
        access_token or ""
    ).strip()

    clean_refresh_token = str(
        refresh_token or ""
    ).strip()

    if not clean_access_token:
        raise ValueError(
            "Supabase access token is required."
        )

    if not clean_refresh_token:
        raise ValueError(
            "Supabase refresh token is required."
        )

    return (
        clean_access_token,
        clean_refresh_token,
    )


def safe_integer(
    value: Any,
    default: int = 0,
) -> int:
    """
    Safely convert a value into integer.
    """

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


# =========================================================
# SAVE VERIFICATION
# =========================================================

def save_verification(
    report_data: dict[str, Any],
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> int:
    """
    Save one TrustGuard verification report to Supabase.

    RLS ensures that a user can insert only a row
    whose user_id matches auth.uid().
    """

    if not isinstance(
        report_data,
        dict,
    ):
        raise TypeError(
            "report_data must be a dictionary."
        )

    clean_user_id = validate_user_id(
        user_id
    )

    (
        clean_access_token,
        clean_refresh_token,
    ) = validate_tokens(
        access_token,
        refresh_token,
    )

    client = create_authenticated_client(
        access_token=clean_access_token,
        refresh_token=clean_refresh_token,
    )

    record = {
        "user_id": clean_user_id,

        "document_name": str(
            report_data.get(
                "document_name",
                "",
            )
        ),

        "question": str(
            report_data.get(
                "question",
                "",
            )
        ),

        "ai_answer": str(
            report_data.get(
                "original_ai_answer",
                "",
            )
        ),

        "overall_score": safe_integer(
            report_data.get(
                "overall_trust_score",
                0,
            )
        ),

        "trust_level": str(
            report_data.get(
                "trust_level",
                "",
            )
        ),

        "final_verified_response": str(
            report_data.get(
                "final_verified_response",
                "",
            )
        ),

        # JSONB column
        "report_json": report_data,
    }

    response = (
        client
        .table("verifications")
        .insert(record)
        .select("id")
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Verification was not saved to Supabase."
        )

    saved_record = response.data[0]

    record_id = saved_record.get(
        "id"
    )

    if record_id is None:
        raise RuntimeError(
            "Supabase did not return a verification ID."
        )

    return int(
        record_id
    )


# =========================================================
# GET USER VERIFICATION HISTORY
# =========================================================

def get_verification_history(
    user_id: str,
    access_token: str,
    refresh_token: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Return verification history for one logged-in user.
    """

    clean_user_id = validate_user_id(
        user_id
    )

    (
        clean_access_token,
        clean_refresh_token,
    ) = validate_tokens(
        access_token,
        refresh_token,
    )

    try:
        safe_limit = int(
            limit
        )

    except (
        TypeError,
        ValueError,
    ):
        safe_limit = 100

    safe_limit = max(
        1,
        min(
            safe_limit,
            500,
        ),
    )

    client = create_authenticated_client(
        access_token=clean_access_token,
        refresh_token=clean_refresh_token,
    )

    response = (
        client
        .table("verifications")
        .select(
            (
                "id,"
                "created_at,"
                "document_name,"
                "question,"
                "overall_score,"
                "trust_level"
            )
        )
        .eq(
            "user_id",
            clean_user_id,
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(
            safe_limit
        )
        .execute()
    )

    if not response.data:
        return []

    return list(
        response.data
    )


# =========================================================
# GET ONE VERIFICATION REPORT
# =========================================================

def get_verification_details(
    record_id: int,
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> dict[str, Any] | None:
    """
    Return one user's verification report.

    Both the explicit user filter and RLS protect the row.
    """

    try:
        safe_record_id = int(
            record_id
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if safe_record_id <= 0:
        return None

    clean_user_id = validate_user_id(
        user_id
    )

    (
        clean_access_token,
        clean_refresh_token,
    ) = validate_tokens(
        access_token,
        refresh_token,
    )

    client = create_authenticated_client(
        access_token=clean_access_token,
        refresh_token=clean_refresh_token,
    )

    response = (
        client
        .table("verifications")
        .select(
            "id, user_id, report_json"
        )
        .eq(
            "id",
            safe_record_id,
        )
        .eq(
            "user_id",
            clean_user_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    record = response.data[0]

    report = record.get(
        "report_json"
    )

    if not isinstance(
        report,
        dict,
    ):
        return None

    return report


# =========================================================
# DELETE VERIFICATION
# =========================================================

def delete_verification(
    record_id: int,
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> bool:
    """
    Delete a verification report belonging to
    the logged-in user.
    """

    try:
        safe_record_id = int(
            record_id
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    if safe_record_id <= 0:
        return False

    clean_user_id = validate_user_id(
        user_id
    )

    (
        clean_access_token,
        clean_refresh_token,
    ) = validate_tokens(
        access_token,
        refresh_token,
    )

    client = create_authenticated_client(
        access_token=clean_access_token,
        refresh_token=clean_refresh_token,
    )

    # First confirm that the user can see this row.
    existing_response = (
        client
        .table("verifications")
        .select("id")
        .eq(
            "id",
            safe_record_id,
        )
        .eq(
            "user_id",
            clean_user_id,
        )
        .limit(1)
        .execute()
    )

    if not existing_response.data:
        return False

    (
        client
        .table("verifications")
        .delete()
        .eq(
            "id",
            safe_record_id,
        )
        .eq(
            "user_id",
            clean_user_id,
        )
        .execute()
    )

    return True