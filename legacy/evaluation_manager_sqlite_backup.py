from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

from modules.database_manager import get_connection


# =========================================================
# CONSTANTS
# =========================================================

STATUS_LABELS = (
    "Verified",
    "Partially Verified",
    "Unsupported",
    "Incorrect",
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_evaluation_database() -> None:
    """
    Create the evaluation_labels table.

    Each row stores:
    - System-predicted claim status
    - Manually assigned correct status
    - User and verification report information
    """

    create_table_query = """
    CREATE TABLE IF NOT EXISTS evaluation_labels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        verification_id INTEGER NOT NULL,
        claim_index INTEGER NOT NULL,
        claim_text TEXT NOT NULL,
        predicted_status TEXT NOT NULL,
        expected_status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (
            user_id,
            verification_id,
            claim_index
        )
    )
    """

    with get_connection() as connection:
        connection.execute(create_table_query)

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_evaluation_user_id
            ON evaluation_labels(user_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_evaluation_verification_id
            ON evaluation_labels(verification_id)
            """
        )

        connection.commit()


# =========================================================
# VALIDATION
# =========================================================

def normalize_status(
    status: Any,
) -> str:
    """
    Convert a status into one of the supported labels.
    """

    clean_status = str(
        status or ""
    ).strip()

    if clean_status in STATUS_LABELS:
        return clean_status

    return "Unsupported"


def validate_positive_integer(
    value: Any,
    field_name: str,
) -> int:
    """
    Convert a value into a positive integer.
    """

    try:
        converted_value = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{field_name} must be a valid number."
        ) from error

    if converted_value <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero."
        )

    return converted_value


# =========================================================
# SAVE GROUND-TRUTH LABELS
# =========================================================

def save_ground_truth_labels(
    user_id: int,
    verification_id: int,
    labels: list[dict[str, Any]],
) -> int:
    """
    Save or update manually assigned expected statuses.

    Args:
        user_id:
            Logged-in user ID.

        verification_id:
            Selected verification report ID.

        labels:
            List containing claim index, claim text,
            predicted status and expected status.

    Returns:
        Number of labels saved.
    """

    safe_user_id = validate_positive_integer(
        user_id,
        "User ID",
    )

    safe_verification_id = validate_positive_integer(
        verification_id,
        "Verification ID",
    )

    if not labels:
        raise ValueError(
            "At least one evaluation label is required."
        )

    current_time = datetime.now().isoformat(
        timespec="seconds"
    )

    query = """
    INSERT INTO evaluation_labels (
        user_id,
        verification_id,
        claim_index,
        claim_text,
        predicted_status,
        expected_status,
        created_at,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)

    ON CONFLICT (
        user_id,
        verification_id,
        claim_index
    )
    DO UPDATE SET
        claim_text = excluded.claim_text,
        predicted_status = excluded.predicted_status,
        expected_status = excluded.expected_status,
        updated_at = excluded.updated_at
    """

    saved_count = 0

    with get_connection() as connection:
        for label in labels:
            claim_index = validate_positive_integer(
                label.get("claim_index"),
                "Claim index",
            )

            claim_text = str(
                label.get(
                    "claim_text",
                    "",
                )
            ).strip()

            predicted_status = normalize_status(
                label.get(
                    "predicted_status"
                )
            )

            expected_status = normalize_status(
                label.get(
                    "expected_status"
                )
            )

            if not claim_text:
                continue

            connection.execute(
                query,
                (
                    safe_user_id,
                    safe_verification_id,
                    claim_index,
                    claim_text,
                    predicted_status,
                    expected_status,
                    current_time,
                    current_time,
                ),
            )

            saved_count += 1

        connection.commit()

    return saved_count


# =========================================================
# LOAD LABELS
# =========================================================

def get_report_evaluation_labels(
    user_id: int,
    verification_id: int,
) -> dict[int, str]:
    """
    Return existing expected statuses for one report.

    Returns:
        Dictionary in the format:
        {
            claim_index: expected_status
        }
    """

    safe_user_id = validate_positive_integer(
        user_id,
        "User ID",
    )

    safe_verification_id = validate_positive_integer(
        verification_id,
        "Verification ID",
    )

    query = """
    SELECT
        claim_index,
        expected_status
    FROM evaluation_labels
    WHERE user_id = ?
      AND verification_id = ?
    ORDER BY claim_index ASC
    """

    with get_connection() as connection:
        rows = connection.execute(
            query,
            (
                safe_user_id,
                safe_verification_id,
            ),
        ).fetchall()

    return {
        int(row["claim_index"]): row[
            "expected_status"
        ]
        for row in rows
    }


def get_evaluation_rows(
    user_id: int,
    verification_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Return evaluation rows for one user.

    When verification_id is supplied, only labels belonging
    to that report are returned.
    """

    safe_user_id = validate_positive_integer(
        user_id,
        "User ID",
    )

    if verification_id is None:
        query = """
        SELECT
            id,
            verification_id,
            claim_index,
            claim_text,
            predicted_status,
            expected_status,
            created_at,
            updated_at
        FROM evaluation_labels
        WHERE user_id = ?
        ORDER BY verification_id DESC, claim_index ASC
        """

        parameters = (
            safe_user_id,
        )

    else:
        safe_verification_id = validate_positive_integer(
            verification_id,
            "Verification ID",
        )

        query = """
        SELECT
            id,
            verification_id,
            claim_index,
            claim_text,
            predicted_status,
            expected_status,
            created_at,
            updated_at
        FROM evaluation_labels
        WHERE user_id = ?
          AND verification_id = ?
        ORDER BY claim_index ASC
        """

        parameters = (
            safe_user_id,
            safe_verification_id,
        )

    with get_connection() as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# DELETE EVALUATION LABELS
# =========================================================

def delete_report_evaluation(
    user_id: int,
    verification_id: int,
) -> bool:
    """
    Delete manual evaluation labels for one report.
    """

    safe_user_id = validate_positive_integer(
        user_id,
        "User ID",
    )

    safe_verification_id = validate_positive_integer(
        verification_id,
        "Verification ID",
    )

    query = """
    DELETE FROM evaluation_labels
    WHERE user_id = ?
      AND verification_id = ?
    """

    with get_connection() as connection:
        cursor = connection.execute(
            query,
            (
                safe_user_id,
                safe_verification_id,
            ),
        )

        connection.commit()

    return cursor.rowcount > 0


# =========================================================
# METRIC CALCULATION
# =========================================================

def calculate_evaluation_metrics(
    evaluation_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate classification evaluation metrics.

    Returns:
    - Accuracy
    - Macro Precision
    - Macro Recall
    - Macro F1 Score
    - Per-class metrics
    - Confusion matrix
    """

    if not evaluation_rows:
        return {
            "total_claims": 0,
            "correct_predictions": 0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "per_class_metrics": [],
            "confusion_matrix": [],
        }

    expected_statuses = [
        normalize_status(
            row.get(
                "expected_status"
            )
        )
        for row in evaluation_rows
    ]

    predicted_statuses = [
        normalize_status(
            row.get(
                "predicted_status"
            )
        )
        for row in evaluation_rows
    ]

    accuracy = accuracy_score(
        expected_statuses,
        predicted_statuses,
    )

    (
        macro_precision,
        macro_recall,
        macro_f1,
        _,
    ) = precision_recall_fscore_support(
        expected_statuses,
        predicted_statuses,
        labels=list(STATUS_LABELS),
        average="macro",
        zero_division=0,
    )

    (
        class_precision,
        class_recall,
        class_f1,
        class_support,
    ) = precision_recall_fscore_support(
        expected_statuses,
        predicted_statuses,
        labels=list(STATUS_LABELS),
        average=None,
        zero_division=0,
    )

    matrix = confusion_matrix(
        expected_statuses,
        predicted_statuses,
        labels=list(STATUS_LABELS),
    )

    correct_predictions = sum(
        expected == predicted
        for expected, predicted in zip(
            expected_statuses,
            predicted_statuses,
        )
    )

    per_class_metrics = []

    for index, status in enumerate(
        STATUS_LABELS
    ):
        per_class_metrics.append(
            {
                "status": status,
                "precision": round(
                    float(
                        class_precision[index]
                    )
                    * 100,
                    2,
                ),
                "recall": round(
                    float(
                        class_recall[index]
                    )
                    * 100,
                    2,
                ),
                "f1_score": round(
                    float(
                        class_f1[index]
                    )
                    * 100,
                    2,
                ),
                "support": int(
                    class_support[index]
                ),
            }
        )

    confusion_matrix_rows = []

    for row_index, actual_status in enumerate(
        STATUS_LABELS
    ):
        matrix_row = {
            "Actual Status": actual_status,
        }

        for column_index, predicted_status in enumerate(
            STATUS_LABELS
        ):
            matrix_row[
                f"Predicted: {predicted_status}"
            ] = int(
                matrix[
                    row_index,
                    column_index,
                ]
            )

        confusion_matrix_rows.append(
            matrix_row
        )

    return {
        "total_claims": len(
            evaluation_rows
        ),
        "correct_predictions": int(
            correct_predictions
        ),
        "accuracy": round(
            float(accuracy) * 100,
            2,
        ),
        "precision": round(
            float(macro_precision) * 100,
            2,
        ),
        "recall": round(
            float(macro_recall) * 100,
            2,
        ),
        "f1_score": round(
            float(macro_f1) * 100,
            2,
        ),
        "per_class_metrics": (
            per_class_metrics
        ),
        "confusion_matrix": (
            confusion_matrix_rows
        ),
    }