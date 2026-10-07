from __future__ import annotations

from collections import defaultdict
from typing import Any

from modules.supabase_manager import (
    create_authenticated_client,
)


VALID_ROLES = {
    "user",
    "admin",
}

VALID_CLAIM_STATUSES = {
    "Verified",
    "Partially Verified",
    "Unsupported",
    "Incorrect",
}


# =========================================================
# HELPERS
# =========================================================

def validate_user_id(user_id: Any) -> str:
    """
    Supabase user ID is a UUID string.
    """

    clean_user_id = str(
        user_id or ""
    ).strip()

    if not clean_user_id:
        raise ValueError(
            "Valid Supabase user ID is required."
        )

    return clean_user_id


def validate_tokens(
    access_token: str,
    refresh_token: str,
) -> tuple[str, str]:

    access_token = str(
        access_token or ""
    ).strip()

    refresh_token = str(
        refresh_token or ""
    ).strip()

    if not access_token:
        raise ValueError(
            "Access token is required."
        )

    if not refresh_token:
        raise ValueError(
            "Refresh token is required."
        )

    return (
        access_token,
        refresh_token,
    )


def safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


# =========================================================
# ADMIN CLIENT
# =========================================================

def get_admin_client(
    user_id: str,
    access_token: str,
    refresh_token: str,
):
    """
    Create authenticated Supabase client
    and confirm logged-in user is admin.
    """

    user_id = validate_user_id(
        user_id
    )

    access_token, refresh_token = (
        validate_tokens(
            access_token,
            refresh_token,
        )
    )

    client = create_authenticated_client(
        access_token=access_token,
        refresh_token=refresh_token,
    )

    response = (
        client
        .table("profiles")
        .select(
            "id, username, role"
        )
        .eq(
            "id",
            user_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        raise PermissionError(
            "Admin profile was not found."
        )

    profile = response.data[0]

    role = str(
        profile.get(
            "role",
            "user",
        )
    ).lower()

    if role != "admin":
        raise PermissionError(
            "Administrator access is required."
        )

    return client


# =========================================================
# COUNT
# =========================================================

def get_exact_count(
    client,
    table_name: str,
) -> int:

    response = (
        client
        .table(table_name)
        .select(
            "id",
            count="exact",
        )
        .limit(1)
        .execute()
    )

    count = getattr(
        response,
        "count",
        None,
    )

    if count is None:
        return len(
            response.data or []
        )

    return int(count)


# =========================================================
# ADMIN STATISTICS
# =========================================================

def get_admin_statistics(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> dict[str, Any]:

    client = get_admin_client(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    total_users = get_exact_count(
        client,
        "profiles",
    )

    total_verifications = get_exact_count(
        client,
        "verifications",
    )

    total_evaluated_claims = get_exact_count(
        client,
        "evaluation_labels",
    )

    response = (
        client
        .table("verifications")
        .select(
            "user_id, overall_score"
        )
        .execute()
    )

    rows = response.data or []

    scores = []

    active_users = set()

    for row in rows:

        row_user_id = row.get(
            "user_id"
        )

        if row_user_id:
            active_users.add(
                str(row_user_id)
            )

        scores.append(
            safe_int(
                row.get(
                    "overall_score",
                    0,
                )
            )
        )

    if scores:

        average_score = (
            sum(scores)
            / len(scores)
        )

        highest_score = max(
            scores
        )

        lowest_score = min(
            scores
        )

    else:

        average_score = 0.0
        highest_score = 0
        lowest_score = 0

    return {
        "total_users": (
            total_users
        ),

        "total_verifications": (
            total_verifications
        ),

        "active_users": len(
            active_users
        ),

        "total_evaluated_claims": (
            total_evaluated_claims
        ),

        "average_score": round(
            average_score,
            2,
        ),

        "highest_score": (
            highest_score
        ),

        "lowest_score": (
            lowest_score
        ),
    }


# =========================================================
# RECENT USERS
# =========================================================

def get_recent_users(
    user_id: str,
    access_token: str,
    refresh_token: str,
    limit: int = 20,
) -> list[dict[str, Any]]:

    client = get_admin_client(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    limit = max(
        1,
        min(
            safe_int(
                limit,
                20,
            ),
            100,
        ),
    )

    response = (
        client
        .table("profiles")
        .select(
            "id, username, role, created_at"
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(
            limit
        )
        .execute()
    )

    return list(
        response.data or []
    )


# =========================================================
# RECENT VERIFICATIONS
# =========================================================

def get_recent_verifications(
    user_id: str,
    access_token: str,
    refresh_token: str,
    limit: int = 30,
) -> list[dict[str, Any]]:

    client = get_admin_client(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    limit = max(
        1,
        min(
            safe_int(
                limit,
                30,
            ),
            200,
        ),
    )

    verification_response = (
        client
        .table("verifications")
        .select(
            (
                "id,"
                "user_id,"
                "created_at,"
                "document_name,"
                "question,"
                "overall_score,"
                "trust_level"
            )
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(
            limit
        )
        .execute()
    )

    profile_response = (
        client
        .table("profiles")
        .select(
            "id, username"
        )
        .execute()
    )

    profile_map = {
        str(row["id"]): row.get(
            "username",
            "Unknown User",
        )
        for row in (
            profile_response.data
            or []
        )
    }

    results = []

    for row in (
        verification_response.data
        or []
    ):

        verification_user_id = str(
            row.get(
                "user_id",
                "",
            )
        )

        results.append(
            {
                "id": row.get(
                    "id"
                ),

                "username": (
                    profile_map.get(
                        verification_user_id,
                        "Unknown User",
                    )
                ),

                "created_at": row.get(
                    "created_at"
                ),

                "document_name": row.get(
                    "document_name"
                ),

                "question": row.get(
                    "question"
                ),

                "overall_score": safe_int(
                    row.get(
                        "overall_score",
                        0,
                    )
                ),

                "trust_level": row.get(
                    "trust_level"
                ),
            }
        )

    return results


# =========================================================
# USER ACTIVITY
# =========================================================

def get_user_activity(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> list[dict[str, Any]]:

    client = get_admin_client(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    profiles_response = (
        client
        .table("profiles")
        .select(
            "id, username, role, created_at"
        )
        .execute()
    )

    verifications_response = (
        client
        .table("verifications")
        .select(
            "id, user_id, created_at, overall_score"
        )
        .execute()
    )

    profiles = (
        profiles_response.data
        or []
    )

    verifications = (
        verifications_response.data
        or []
    )

    activity = defaultdict(
        lambda: {
            "count": 0,
            "scores": [],
            "last_verification": None,
        }
    )

    for verification in verifications:

        verification_user_id = str(
            verification.get(
                "user_id",
                "",
            )
        )

        user_activity = activity[
            verification_user_id
        ]

        user_activity[
            "count"
        ] += 1

        user_activity[
            "scores"
        ].append(
            safe_int(
                verification.get(
                    "overall_score",
                    0,
                )
            )
        )

        created_at = verification.get(
            "created_at"
        )

        if (
            created_at
            and (
                user_activity[
                    "last_verification"
                ]
                is None
                or created_at
                > user_activity[
                    "last_verification"
                ]
            )
        ):
            user_activity[
                "last_verification"
            ] = created_at

    results = []

    for profile in profiles:

        profile_id = str(
            profile.get(
                "id",
                "",
            )
        )

        current = activity[
            profile_id
        ]

        scores = current[
            "scores"
        ]

        if scores:
            average_score = (
                sum(scores)
                / len(scores)
            )
        else:
            average_score = 0.0

        results.append(
            {
                "user_id": (
                    profile_id
                ),

                "username": profile.get(
                    "username",
                    "Unknown",
                ),

                "role": profile.get(
                    "role",
                    "user",
                ),

                "registered_at": profile.get(
                    "created_at"
                ),

                "verification_count": (
                    current[
                        "count"
                    ]
                ),

                "average_trust_score": round(
                    average_score,
                    2,
                ),

                "last_verification": (
                    current[
                        "last_verification"
                    ]
                ),
            }
        )

    results.sort(
        key=lambda item: item[
            "verification_count"
        ],
        reverse=True,
    )

    return results


# =========================================================
# SCORE DISTRIBUTION
# =========================================================

def get_score_distribution(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> list[dict[str, Any]]:

    client = get_admin_client(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    response = (
        client
        .table("verifications")
        .select(
            "overall_score"
        )
        .execute()
    )

    distribution = {
        "80-100 High": 0,
        "60-79 Medium": 0,
        "40-59 Low": 0,
        "0-39 Very Low": 0,
    }

    for row in (
        response.data
        or []
    ):

        score = safe_int(
            row.get(
                "overall_score",
                0,
            )
        )

        if score >= 80:

            distribution[
                "80-100 High"
            ] += 1

        elif score >= 60:

            distribution[
                "60-79 Medium"
            ] += 1

        elif score >= 40:

            distribution[
                "40-59 Low"
            ] += 1

        else:

            distribution[
                "0-39 Very Low"
            ] += 1

    return [
        {
            "score_range": key,
            "report_count": value,
        }
        for key, value
        in distribution.items()
    ]


# =========================================================
# CLAIM STATUS DISTRIBUTION
# =========================================================

def get_claim_status_distribution(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> list[dict[str, Any]]:

    client = get_admin_client(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    response = (
        client
        .table("verifications")
        .select(
            "report_json"
        )
        .execute()
    )

    counts = {
        "Verified": 0,
        "Partially Verified": 0,
        "Unsupported": 0,
        "Incorrect": 0,
    }

    for row in (
        response.data
        or []
    ):

        report = row.get(
            "report_json"
        )

        if not isinstance(
            report,
            dict,
        ):
            continue

        claims = report.get(
            "claim_results",
            [],
        )

        for claim in claims:

            status = str(
                claim.get(
                    "status",
                    "Unsupported",
                )
            )

            if (
                status
                in VALID_CLAIM_STATUSES
            ):

                counts[
                    status
                ] += 1

    return [
        {
            "status": status,
            "claim_count": count,
        }
        for status, count
        in counts.items()
    ]


# =========================================================
# USER DETAILS
# =========================================================

def get_user_details(
    target_user_id: str,
    acting_admin_id: str,
    access_token: str,
    refresh_token: str,
) -> dict[str, Any] | None:

    target_user_id = validate_user_id(
        target_user_id
    )

    client = get_admin_client(
        user_id=acting_admin_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    profile_response = (
        client
        .table("profiles")
        .select(
            "id, username, role, created_at"
        )
        .eq(
            "id",
            target_user_id,
        )
        .limit(1)
        .execute()
    )

    if not profile_response.data:
        return None

    profile = (
        profile_response.data[0]
    )

    verification_response = (
        client
        .table("verifications")
        .select(
            "overall_score, created_at"
        )
        .eq(
            "user_id",
            target_user_id,
        )
        .order(
            "created_at",
            desc=True,
        )
        .execute()
    )

    verification_rows = (
        verification_response.data
        or []
    )

    scores = [
        safe_int(
            row.get(
                "overall_score",
                0,
            )
        )
        for row
        in verification_rows
    ]

    average_score = (
        sum(scores)
        / len(scores)
        if scores
        else 0.0
    )

    last_verification = None

    if verification_rows:
        last_verification = (
            verification_rows[0]
            .get(
                "created_at"
            )
        )

    return {
        "id": profile.get(
            "id"
        ),

        "username": profile.get(
            "username",
            "Unknown",
        ),

        "role": profile.get(
            "role",
            "user",
        ),

        "created_at": profile.get(
            "created_at"
        ),

        "verification_count": len(
            verification_rows
        ),

        "average_trust_score": round(
            average_score,
            2,
        ),

        "last_verification": (
            last_verification
        ),
    }


# =========================================================
# ADMIN COUNT
# =========================================================

def count_admin_accounts(
    acting_admin_id: str,
    access_token: str,
    refresh_token: str,
) -> int:

    client = get_admin_client(
        user_id=acting_admin_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    response = (
        client
        .table("profiles")
        .select(
            "id",
            count="exact",
        )
        .eq(
            "role",
            "admin",
        )
        .execute()
    )

    count = getattr(
        response,
        "count",
        None,
    )

    if count is not None:
        return int(count)

    return len(
        response.data or []
    )


# =========================================================
# CHANGE USER ROLE
# =========================================================

def change_user_role(
    target_user_id: str,
    new_role: str,
    acting_admin_id: str,
    access_token: str,
    refresh_token: str,
) -> tuple[bool, str]:

    target_user_id = validate_user_id(
        target_user_id
    )

    acting_admin_id = validate_user_id(
        acting_admin_id
    )

    new_role = str(
        new_role or ""
    ).strip().lower()

    if new_role not in VALID_ROLES:

        return (
            False,
            "Role must be user or admin.",
        )

    if (
        target_user_id
        == acting_admin_id
    ):

        return (
            False,
            "You cannot change your own role.",
        )

    client = get_admin_client(
        user_id=acting_admin_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    response = (
        client
        .table("profiles")
        .select(
            "id, username, role"
        )
        .eq(
            "id",
            target_user_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:

        return (
            False,
            "Selected user was not found.",
        )

    target_user = (
        response.data[0]
    )

    username = target_user.get(
        "username",
        "User",
    )

    current_role = str(
        target_user.get(
            "role",
            "user",
        )
    ).lower()

    if current_role == new_role:

        return (
            False,
            f"{username} already has "
            f"the {new_role} role.",
        )

    if (
        current_role == "admin"
        and new_role == "user"
    ):

        admin_count = count_admin_accounts(
            acting_admin_id=(
                acting_admin_id
            ),
            access_token=(
                access_token
            ),
            refresh_token=(
                refresh_token
            ),
        )

        if admin_count <= 1:

            return (
                False,
                "The final administrator "
                "cannot be demoted.",
            )

    update_response = (
        client
        .table("profiles")
        .update(
            {
                "role": new_role
            }
        )
        .eq(
            "id",
            target_user_id,
        )
        .select(
            "id, username, role"
        )
        .execute()
    )

    if not update_response.data:

        return (
            False,
            "Role update failed or was blocked by RLS.",
        )

    return (
        True,
        f"{username}'s role changed "
        f"to {new_role} successfully.",
    )