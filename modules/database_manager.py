import json
import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIRECTORY = PROJECT_ROOT / "database"
DATABASE_PATH = DATABASE_DIRECTORY / "trustguard.db"


def get_connection() -> sqlite3.Connection:
    """
    Create and return a SQLite database connection.
    """

    DATABASE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10,
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database() -> None:
    """
    Create the verification table and migrate older databases
    by adding a user_id column when required.
    """

    create_table_query = """
    CREATE TABLE IF NOT EXISTS verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        created_at TEXT NOT NULL,
        document_name TEXT NOT NULL,
        question TEXT NOT NULL,
        ai_answer TEXT NOT NULL,
        overall_score INTEGER NOT NULL,
        trust_level TEXT NOT NULL,
        final_verified_response TEXT NOT NULL,
        report_json TEXT NOT NULL
    )
    """

    with get_connection() as connection:
        connection.execute(create_table_query)

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(verifications)"
            ).fetchall()
        }

        # Migration for the old shared-history database
        if "user_id" not in columns:
            connection.execute(
                """
                ALTER TABLE verifications
                ADD COLUMN user_id INTEGER
                """
            )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_verifications_user_id
            ON verifications(user_id)
            """
        )

        connection.commit()


def save_verification(
    report_data: dict[str, Any],
    user_id: int,
) -> int:
    """
    Save a verification report for one logged-in user.

    Returns:
        Newly created verification record ID.
    """

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(
            "A valid logged-in user ID is required."
        )

    query = """
    INSERT INTO verifications (
        user_id,
        created_at,
        document_name,
        question,
        ai_answer,
        overall_score,
        trust_level,
        final_verified_response,
        report_json
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    values = (
        user_id,
        report_data.get("report_generated_at", ""),
        report_data.get("document_name", ""),
        report_data.get("question", ""),
        report_data.get("original_ai_answer", ""),
        int(report_data.get("overall_trust_score", 0)),
        report_data.get("trust_level", ""),
        report_data.get("final_verified_response", ""),
        json.dumps(
            report_data,
            ensure_ascii=False,
        ),
    )

    with get_connection() as connection:
        cursor = connection.execute(
            query,
            values,
        )

        connection.commit()

        return int(cursor.lastrowid)


def get_verification_history(
    user_id: int,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Return verification history belonging only to one user.
    """

    if not isinstance(user_id, int) or user_id <= 0:
        return []

    safe_limit = max(
        1,
        min(int(limit), 500),
    )

    query = """
    SELECT
        id,
        created_at,
        document_name,
        question,
        overall_score,
        trust_level
    FROM verifications
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT ?
    """

    with get_connection() as connection:
        rows = connection.execute(
            query,
            (
                user_id,
                safe_limit,
            ),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_verification_details(
    record_id: int,
    user_id: int,
) -> dict[str, Any] | None:
    """
    Return a report only when it belongs to the given user.
    """

    query = """
    SELECT report_json
    FROM verifications
    WHERE id = ?
      AND user_id = ?
    LIMIT 1
    """

    with get_connection() as connection:
        row = connection.execute(
            query,
            (
                record_id,
                user_id,
            ),
        ).fetchone()

    if row is None:
        return None

    try:
        return json.loads(
            row["report_json"]
        )

    except json.JSONDecodeError:
        return None


def delete_verification(
    record_id: int,
    user_id: int,
) -> bool:
    """
    Delete a record only when it belongs to the given user.
    """

    query = """
    DELETE FROM verifications
    WHERE id = ?
      AND user_id = ?
    """

    with get_connection() as connection:
        cursor = connection.execute(
            query,
            (
                record_id,
                user_id,
            ),
        )

        connection.commit()

        return cursor.rowcount > 0