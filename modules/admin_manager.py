import json
import sqlite3
from typing import Any

from modules.database_manager import get_connection


VALID_STATUSES = {
    "Verified",
    "Partially Verified",
    "Unsupported",
    "Incorrect",
}


def get_admin_statistics() -> dict[str, Any]:
    """
    Return main system statistics for the admin dashboard.
    """

    with get_connection() as connection:
        total_users = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM users
            """
        ).fetchone()["total"]

        total_verifications = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM verifications
            """
        ).fetchone()["total"]

        active_users = connection.execute(
            """
            SELECT COUNT(DISTINCT user_id) AS total
            FROM verifications
            WHERE user_id IS NOT NULL
            """
        ).fetchone()["total"]

        score_row = connection.execute(
            """
            SELECT
                COALESCE(AVG(overall_score), 0) AS average_score,
                COALESCE(MAX(overall_score), 0) AS highest_score,
                COALESCE(MIN(overall_score), 0) AS lowest_score
            FROM verifications
            """
        ).fetchone()

    return {
        "total_users": int(total_users or 0),
        "total_verifications": int(
            total_verifications or 0
        ),
        "active_users": int(active_users or 0),
        "average_score": round(
            float(score_row["average_score"] or 0),
            2,
        ),
        "highest_score": int(
            score_row["highest_score"] or 0
        ),
        "lowest_score": int(
            score_row["lowest_score"] or 0
        ),
    }


def get_recent_users(
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Return recently registered users.
    """

    safe_limit = max(
        1,
        min(int(limit), 100),
    )

    query = """
    SELECT
        id,
        username,
        email,
        role,
        created_at
    FROM users
    ORDER BY id DESC
    LIMIT ?
    """

    with get_connection() as connection:
        rows = connection.execute(
            query,
            (safe_limit,),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_recent_verifications(
    limit: int = 30,
) -> list[dict[str, Any]]:
    """
    Return recent verification reports with usernames.
    """

    safe_limit = max(
        1,
        min(int(limit), 200),
    )

    query = """
    SELECT
        v.id,
        COALESCE(u.username, 'Unknown User') AS username,
        v.created_at,
        v.document_name,
        v.question,
        v.overall_score,
        v.trust_level
    FROM verifications AS v
    LEFT JOIN users AS u
        ON u.id = v.user_id
    ORDER BY v.id DESC
    LIMIT ?
    """

    with get_connection() as connection:
        rows = connection.execute(
            query,
            (safe_limit,),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_user_activity() -> list[dict[str, Any]]:
    """
    Return user-wise verification statistics.
    """

    query = """
    SELECT
        u.id AS user_id,
        u.username,
        u.email,
        u.role,
        COUNT(v.id) AS verification_count,
        COALESCE(
            ROUND(AVG(v.overall_score), 2),
            0
        ) AS average_trust_score,
        MAX(v.created_at) AS last_verification
    FROM users AS u
    LEFT JOIN verifications AS v
        ON v.user_id = u.id
    GROUP BY
        u.id,
        u.username,
        u.email,
        u.role
    ORDER BY verification_count DESC, u.id DESC
    """

    with get_connection() as connection:
        rows = connection.execute(
            query
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_score_distribution() -> list[dict[str, Any]]:
    """
    Return report counts grouped into trust-score ranges.
    """

    query = """
    SELECT
        CASE
            WHEN overall_score >= 80 THEN '80-100 High'
            WHEN overall_score >= 60 THEN '60-79 Medium'
            WHEN overall_score >= 40 THEN '40-59 Low'
            ELSE '0-39 Very Low'
        END AS score_range,
        COUNT(*) AS report_count
    FROM verifications
    GROUP BY score_range
    ORDER BY
        CASE score_range
            WHEN '80-100 High' THEN 1
            WHEN '60-79 Medium' THEN 2
            WHEN '40-59 Low' THEN 3
            ELSE 4
        END
    """

    with get_connection() as connection:
        rows = connection.execute(
            query
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_claim_status_distribution() -> list[dict[str, Any]]:
    """
    Read saved JSON reports and count claim statuses.
    """

    status_counts = {
        "Verified": 0,
        "Partially Verified": 0,
        "Unsupported": 0,
        "Incorrect": 0,
    }

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT report_json
            FROM verifications
            """
        ).fetchall()

    for row in rows:
        try:
            report = json.loads(
                row["report_json"]
            )
        except (
            json.JSONDecodeError,
            TypeError,
        ):
            continue

        claim_results = report.get(
            "claim_results",
            [],
        )

        for claim in claim_results:
            status = claim.get(
                "status",
                "Unsupported",
            )

            if status in VALID_STATUSES:
                status_counts[status] += 1

    return [
        {
            "status": status,
            "claim_count": count,
        }
        for status, count in status_counts.items()
    ]
# =========================================================
# ADMIN USER MANAGEMENT
# =========================================================

VALID_USER_ROLES = {
    "user",
    "admin",
}


def get_user_details(
    user_id: int,
) -> dict[str, Any] | None:
    """
    Return one user's public information and activity.

    Password hash and password salt are never returned.
    """

    try:
        safe_user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    if safe_user_id <= 0:
        return None

    query = """
    SELECT
        u.id,
        u.username,
        u.email,
        u.role,
        u.created_at,
        COUNT(v.id) AS verification_count,
        COALESCE(
            ROUND(AVG(v.overall_score), 2),
            0
        ) AS average_trust_score,
        MAX(v.created_at) AS last_verification
    FROM users AS u
    LEFT JOIN verifications AS v
        ON v.user_id = u.id
    WHERE u.id = ?
    GROUP BY
        u.id,
        u.username,
        u.email,
        u.role,
        u.created_at
    LIMIT 1
    """

    with get_connection() as connection:
        row = connection.execute(
            query,
            (safe_user_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def count_admin_accounts(
    connection=None,
) -> int:
    """
    Return total number of administrator accounts.
    """

    query = """
    SELECT COUNT(*) AS total
    FROM users
    WHERE role = 'admin'
    """

    if connection is not None:
        row = connection.execute(
            query
        ).fetchone()

        return int(
            row["total"] or 0
        )

    with get_connection() as database_connection:
        row = database_connection.execute(
            query
        ).fetchone()

    return int(
        row["total"] or 0
    )


def user_is_admin(
    user_id: int,
    connection=None,
) -> bool:
    """
    Check whether a user account has the admin role.
    """

    query = """
    SELECT role
    FROM users
    WHERE id = ?
    LIMIT 1
    """

    if connection is not None:
        row = connection.execute(
            query,
            (int(user_id),),
        ).fetchone()

    else:
        with get_connection() as database_connection:
            row = database_connection.execute(
                query,
                (int(user_id),),
            ).fetchone()

    return bool(
        row is not None
        and row["role"] == "admin"
    )


def change_user_role(
    target_user_id: int,
    new_role: str,
    acting_admin_id: int,
) -> tuple[bool, str]:
    """
    Change a user's role.

    Safety rules:
    - Only an admin can perform this action.
    - Admin cannot change their own role.
    - The final administrator cannot be demoted.
    """

    try:
        safe_target_id = int(
            target_user_id
        )

        safe_admin_id = int(
            acting_admin_id
        )

    except (TypeError, ValueError):
        return (
            False,
            "Invalid user ID.",
        )

    clean_role = str(
        new_role
    ).strip().lower()

    if clean_role not in VALID_USER_ROLES:
        return (
            False,
            "Role must be user or admin.",
        )

    if safe_target_id == safe_admin_id:
        return (
            False,
            "You cannot change your own account role.",
        )

    connection = get_connection()

    try:
        connection.execute(
            "BEGIN IMMEDIATE"
        )

        if not user_is_admin(
            safe_admin_id,
            connection=connection,
        ):
            connection.rollback()

            return (
                False,
                "Only an administrator can change user roles.",
            )

        target_user = connection.execute(
            """
            SELECT
                id,
                username,
                role
            FROM users
            WHERE id = ?
            LIMIT 1
            """,
            (safe_target_id,),
        ).fetchone()

        if target_user is None:
            connection.rollback()

            return (
                False,
                "Selected user account was not found.",
            )

        current_role = (
            target_user["role"]
            or "user"
        )

        username = target_user[
            "username"
        ]

        if current_role == clean_role:
            connection.rollback()

            return (
                False,
                f"{username} already has the "
                f"{clean_role} role.",
            )

        if (
            current_role == "admin"
            and clean_role == "user"
        ):
            total_admins = count_admin_accounts(
                connection=connection
            )

            if total_admins <= 1:
                connection.rollback()

                return (
                    False,
                    "The final administrator account "
                    "cannot be demoted.",
                )

        connection.execute(
            """
            UPDATE users
            SET role = ?
            WHERE id = ?
            """,
            (
                clean_role,
                safe_target_id,
            ),
        )

        connection.commit()

        return (
            True,
            f"{username}'s role changed to "
            f"{clean_role} successfully.",
        )

    except sqlite3.Error as error:
        connection.rollback()

        return (
            False,
            f"Database error: {error}",
        )

    finally:
        connection.close()


def delete_user_account(
    target_user_id: int,
    acting_admin_id: int,
    delete_verification_history: bool = False,
) -> tuple[bool, str]:
    """
    Delete a selected user account.

    When delete_verification_history is False:
        Reports are preserved but their user_id becomes NULL.

    When delete_verification_history is True:
        User reports are permanently deleted.
    """

    try:
        safe_target_id = int(
            target_user_id
        )

        safe_admin_id = int(
            acting_admin_id
        )

    except (TypeError, ValueError):
        return (
            False,
            "Invalid user ID.",
        )

    if safe_target_id == safe_admin_id:
        return (
            False,
            "You cannot delete your own account.",
        )

    connection = get_connection()

    try:
        connection.execute(
            "BEGIN IMMEDIATE"
        )

        if not user_is_admin(
            safe_admin_id,
            connection=connection,
        ):
            connection.rollback()

            return (
                False,
                "Only an administrator can delete accounts.",
            )

        target_user = connection.execute(
            """
            SELECT
                id,
                username,
                role
            FROM users
            WHERE id = ?
            LIMIT 1
            """,
            (safe_target_id,),
        ).fetchone()

        if target_user is None:
            connection.rollback()

            return (
                False,
                "Selected user account was not found.",
            )

        username = target_user[
            "username"
        ]

        target_role = (
            target_user["role"]
            or "user"
        )

        if target_role == "admin":
            total_admins = count_admin_accounts(
                connection=connection
            )

            if total_admins <= 1:
                connection.rollback()

                return (
                    False,
                    "The final administrator account "
                    "cannot be deleted.",
                )

        if delete_verification_history:
            connection.execute(
                """
                DELETE FROM verifications
                WHERE user_id = ?
                """,
                (safe_target_id,),
            )

            history_action = (
                "Verification history was also deleted."
            )

        else:
            connection.execute(
                """
                UPDATE verifications
                SET user_id = NULL
                WHERE user_id = ?
                """,
                (safe_target_id,),
            )

            history_action = (
                "Verification history was preserved anonymously."
            )

        cursor = connection.execute(
            """
            DELETE FROM users
            WHERE id = ?
            """,
            (safe_target_id,),
        )

        if cursor.rowcount == 0:
            connection.rollback()

            return (
                False,
                "Unable to delete the selected account.",
            )

        connection.commit()

        return (
            True,
            f"{username}'s account was deleted. "
            f"{history_action}",
        )

    except sqlite3.Error as error:
        connection.rollback()

        return (
            False,
            f"Database error: {error}",
        )

    finally:
        connection.close()