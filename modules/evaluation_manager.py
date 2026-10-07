from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

from modules.supabase_manager import (
    create_authenticated_client,
)


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
# COMPATIBILITY
# =========================================================

def init_evaluation_database() -> None:
    """
    Evaluation table is now managed by Supabase.

    This function is kept so older pages importing it
    do not break.
    """

    return None


# =========================================================
# VALIDATION HELPERS
# =========================================================

def validate_user_id(
    user_id: Any,
) -> str:
    """
    Validate Supabase UUID user ID.

    IMPORTANT:
    Supabase user IDs are UUID strings, not integers.
    """

    clean_user_id = str(
        user_id or ""
    ).strip()

    if not clean_user_id:
        raise ValueError(
            "Valid Supabase user ID is required."
        )

    return clean_user_id


def validate_verification_id(
    verification_id: Any,
) -> int:
    """
    Validate verification record ID.

    Verification IDs remain integer BIGINT values.
    """

    try:
        clean_id = int(
            verification_id
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            "Verification ID must be a valid integer."
        ) from error

    if clean_id <= 0:
        raise ValueError(
            "Verification ID must be greater than zero."
        )

    return clean_id


def validate_tokens(
    access_token: str,
    refresh_token: str,
) -> tuple[str, str]:
    """
    Validate Supabase authentication tokens.
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


def normalize_status(
    status: Any,
) -> str:
    """
    Normalize verification status.
    """

    clean_status = str(
        status or ""
    ).strip()

    if clean_status in STATUS_LABELS:
        return clean_status

    return "Unsupported"


def utc_timestamp() -> str:
    """
    Return current UTC timestamp.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


# =========================================================
# AUTHENTICATED CLIENT
# =========================================================

def get_authenticated_client(
    access_token: str,
    refresh_token: str,
):
    """
    Create authenticated Supabase client.
    """

    (
        clean_access_token,
        clean_refresh_token,
    ) = validate_tokens(
        access_token,
        refresh_token,
    )

    return create_authenticated_client(
        access_token=clean_access_token,
        refresh_token=clean_refresh_token,
    )


# =========================================================
# VERIFY REPORT OWNERSHIP
# =========================================================

def verification_belongs_to_user(
    user_id: str,
    verification_id: int,
    access_token: str,
    refresh_token: str,
) -> bool:
    """
    Check whether verification belongs to logged-in user.

    RLS also protects this query.
    """

    clean_user_id = validate_user_id(
        user_id
    )

    clean_verification_id = (
        validate_verification_id(
            verification_id
        )
    )

    client = get_authenticated_client(
        access_token,
        refresh_token,
    )

    response = (
        client
        .table("verifications")
        .select("id")
        .eq(
            "id",
            clean_verification_id,
        )
        .eq(
            "user_id",
            clean_user_id,
        )
        .limit(1)
        .execute()
    )

    return bool(
        response.data
    )


# =========================================================
# SAVE / UPDATE GROUND TRUTH
# =========================================================

def save_ground_truth_labels(
    user_id: str,
    verification_id: int,
    labels: list[dict[str, Any]],
    access_token: str,
    refresh_token: str,
) -> int:
    """
    Save manually assigned ground-truth labels
    into Supabase.

    Existing label rows are updated automatically
    using the composite UNIQUE constraint:
        user_id + verification_id + claim_index
    """

    clean_user_id = validate_user_id(
        user_id
    )

    clean_verification_id = (
        validate_verification_id(
            verification_id
        )
    )

    if not labels:
        raise ValueError(
            "At least one claim label is required."
        )

    owns_report = verification_belongs_to_user(
        user_id=clean_user_id,
        verification_id=clean_verification_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    if not owns_report:
        raise PermissionError(
            "Selected verification report does not "
            "belong to the logged-in account."
        )

    client = get_authenticated_client(
        access_token,
        refresh_token,
    )

    now = utc_timestamp()

    rows_to_save = []

    for label in labels:

        try:
            claim_index = int(
                label.get(
                    "claim_index",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if claim_index <= 0:
            continue

        claim_text = str(
            label.get(
                "claim_text",
                "",
            )
        ).strip()

        if not claim_text:
            continue

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

        rows_to_save.append(
            {
                "user_id": clean_user_id,
                "verification_id": (
                    clean_verification_id
                ),
                "claim_index": claim_index,
                "claim_text": claim_text,
                "predicted_status": (
                    predicted_status
                ),
                "expected_status": (
                    expected_status
                ),
                "updated_at": now,
            }
        )

    if not rows_to_save:
        raise ValueError(
            "No valid claim labels were provided."
        )

    response = (
        client
        .table("evaluation_labels")
        .upsert(
            rows_to_save,
            on_conflict=(
                "user_id,"
                "verification_id,"
                "claim_index"
            ),
        )
        .select(
            "id, claim_index"
        )
        .execute()
    )

    if response.data is None:
        return 0

    return len(
        response.data
    )


# =========================================================
# GET SAVED LABELS FOR ONE REPORT
# =========================================================

def get_report_evaluation_labels(
    user_id: str,
    verification_id: int,
    access_token: str,
    refresh_token: str,
) -> dict[int, str]:
    """
    Return saved expected statuses for one report.

    Format:
        {
            1: "Verified",
            2: "Incorrect"
        }
    """

    clean_user_id = validate_user_id(
        user_id
    )

    clean_verification_id = (
        validate_verification_id(
            verification_id
        )
    )

    client = get_authenticated_client(
        access_token,
        refresh_token,
    )

    response = (
        client
        .table("evaluation_labels")
        .select(
            "claim_index, expected_status"
        )
        .eq(
            "user_id",
            clean_user_id,
        )
        .eq(
            "verification_id",
            clean_verification_id,
        )
        .order(
            "claim_index"
        )
        .execute()
    )

    if not response.data:
        return {}

    labels = {}

    for row in response.data:

        try:
            claim_index = int(
                row.get(
                    "claim_index",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if claim_index <= 0:
            continue

        labels[
            claim_index
        ] = normalize_status(
            row.get(
                "expected_status"
            )
        )

    return labels


# =========================================================
# GET EVALUATION ROWS
# =========================================================

def get_evaluation_rows(
    user_id: str,
    access_token: str,
    refresh_token: str,
    verification_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Return evaluation rows belonging to logged-in user.

    verification_id=None:
        Return all evaluated reports.

    verification_id supplied:
        Return labels for one verification report.
    """

    clean_user_id = validate_user_id(
        user_id
    )

    client = get_authenticated_client(
        access_token,
        refresh_token,
    )

    query = (
        client
        .table("evaluation_labels")
        .select(
            (
                "id,"
                "verification_id,"
                "claim_index,"
                "claim_text,"
                "predicted_status,"
                "expected_status,"
                "created_at,"
                "updated_at"
            )
        )
        .eq(
            "user_id",
            clean_user_id,
        )
    )

    if verification_id is not None:

        clean_verification_id = (
            validate_verification_id(
                verification_id
            )
        )

        query = query.eq(
            "verification_id",
            clean_verification_id,
        )

    response = (
        query
        .order(
            "verification_id",
            desc=True,
        )
        .order(
            "claim_index",
            desc=False,
        )
        .execute()
    )

    if not response.data:
        return []

    return list(
        response.data
    )


# =========================================================
# DELETE REPORT EVALUATION
# =========================================================

def delete_report_evaluation(
    user_id: str,
    verification_id: int,
    access_token: str,
    refresh_token: str,
) -> bool:
    """
    Delete manual evaluation labels for one report.

    Original verification report remains saved.
    """

    clean_user_id = validate_user_id(
        user_id
    )

    clean_verification_id = (
        validate_verification_id(
            verification_id
        )
    )

    client = get_authenticated_client(
        access_token,
        refresh_token,
    )

    existing_response = (
        client
        .table("evaluation_labels")
        .select("id")
        .eq(
            "user_id",
            clean_user_id,
        )
        .eq(
            "verification_id",
            clean_verification_id,
        )
        .execute()
    )

    if not existing_response.data:
        return False

    response = (
        client
        .table("evaluation_labels")
        .delete()
        .eq(
            "user_id",
            clean_user_id,
        )
        .eq(
            "verification_id",
            clean_verification_id,
        )
        .select("id")
        .execute()
    )

    return bool(
        response.data
    )


# =========================================================
# CALCULATE PERFORMANCE METRICS
# =========================================================

def calculate_evaluation_metrics(
    evaluation_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate TrustGuard classification performance.

    Metrics:
    - Accuracy
    - Macro Precision
    - Macro Recall
    - Macro F1
    - Per-status metrics
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

    # =====================================================
    # ACCURACY
    # =====================================================

    accuracy = accuracy_score(
        expected_statuses,
        predicted_statuses,
    )

    # =====================================================
    # MACRO METRICS
    # =====================================================

    (
        macro_precision,
        macro_recall,
        macro_f1,
        _,
    ) = precision_recall_fscore_support(
        expected_statuses,
        predicted_statuses,
        labels=list(
            STATUS_LABELS
        ),
        average="macro",
        zero_division=0,
    )

    # =====================================================
    # CLASS-WISE METRICS
    # =====================================================

    (
        class_precision,
        class_recall,
        class_f1,
        class_support,
    ) = precision_recall_fscore_support(
        expected_statuses,
        predicted_statuses,
        labels=list(
            STATUS_LABELS
        ),
        average=None,
        zero_division=0,
    )

    # =====================================================
    # CONFUSION MATRIX
    # =====================================================

    matrix = confusion_matrix(
        expected_statuses,
        predicted_statuses,
        labels=list(
            STATUS_LABELS
        ),
    )

    correct_predictions = sum(
        actual == predicted
        for actual, predicted in zip(
            expected_statuses,
            predicted_statuses,
        )
    )

    # =====================================================
    # PER-CLASS RESULT
    # =====================================================

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

    # =====================================================
    # CONFUSION MATRIX TABLE
    # =====================================================

    confusion_rows = []

    for row_index, actual_status in enumerate(
        STATUS_LABELS
    ):

        matrix_row = {
            "Actual Status": (
                actual_status
            )
        }

        for (
            column_index,
            predicted_status,
        ) in enumerate(
            STATUS_LABELS
        ):

            matrix_row[
                (
                    "Predicted: "
                    f"{predicted_status}"
                )
            ] = int(
                matrix[
                    row_index,
                    column_index,
                ]
            )

        confusion_rows.append(
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
            confusion_rows
        ),
    }