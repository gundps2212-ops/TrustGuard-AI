import pandas as pd
import streamlit as st

from modules.database_manager import (
    get_verification_details,
    get_verification_history,
    init_database,
)
from modules.evaluation_manager import (
    STATUS_LABELS,
    calculate_evaluation_metrics,
    delete_report_evaluation,
    get_evaluation_rows,
    get_report_evaluation_labels,
    init_evaluation_database,
    save_ground_truth_labels,
)


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Evaluation Dashboard",
    page_icon="📈",
    layout="wide",
)

init_database()
init_evaluation_database()


# =========================================================
# LOGIN PROTECTION
# =========================================================

if not st.session_state.get(
    "logged_in",
    False,
):
    st.warning(
        "Please login from the main TrustGuard AI page "
        "to access the Evaluation Dashboard."
    )

    st.stop()


user_id = st.session_state.get(
    "user_id"
)

username = st.session_state.get(
    "username",
    "User",
)


if not user_id:
    st.error(
        "User session is invalid. "
        "Please logout and login again."
    )

    st.stop()


user_id = int(user_id)


# =========================================================
# PAGE HEADER
# =========================================================

st.title(
    "📈 TrustGuard AI Evaluation Dashboard"
)

st.write(
    f"Logged in as **{username}**"
)

st.write(
    "Compare TrustGuard AI's predicted claim statuses "
    "with manually verified correct statuses."
)

st.warning(
    "Expected Status manually select करण्यापूर्वी claim "
    "PDF किंवा trusted source वापरून तपासा. System चा "
    "predicted status पाहून blindly same status select करू नका."
)

st.divider()


# =========================================================
# LOAD VERIFICATION HISTORY
# =========================================================

history_records = get_verification_history(
    user_id=user_id,
    limit=100,
)


if not history_records:
    st.info(
        "No verification reports are available. "
        "First generate and save a verification report."
    )

    st.stop()


report_options = {
    (
        f"Report #{record['id']} | "
        f"{record['question'][:75]} | "
        f"Score: {record['overall_score']}%"
    ): int(record["id"])
    for record in history_records
}


selected_report_label = st.selectbox(
    label="Select verification report",
    options=list(
        report_options.keys()
    ),
)


selected_report_id = report_options[
    selected_report_label
]


selected_report = get_verification_details(
    record_id=selected_report_id,
    user_id=user_id,
)


if selected_report is None:
    st.error(
        "Selected report was not found or does not "
        "belong to your account."
    )

    st.stop()


claim_results = selected_report.get(
    "claim_results",
    [],
)


if not claim_results:
    st.warning(
        "The selected report does not contain "
        "claim verification results."
    )

    st.stop()


# =========================================================
# REPORT INFORMATION
# =========================================================

st.write(
    "## 📄 Selected Report"
)

report_column_1, report_column_2, report_column_3 = (
    st.columns(3)
)


with report_column_1:
    st.metric(
        label="Report ID",
        value=selected_report_id,
    )


with report_column_2:
    st.metric(
        label="Total Claims",
        value=len(claim_results),
    )


with report_column_3:
    st.metric(
        label="Trust Score",
        value=(
            f"{selected_report.get('overall_trust_score', 0)}%"
        ),
    )


st.write("### Question")

st.info(
    selected_report.get(
        "question",
        "Question unavailable.",
    )
)

st.divider()


# =========================================================
# EXISTING LABELS
# =========================================================

existing_labels = get_report_evaluation_labels(
    user_id=user_id,
    verification_id=selected_report_id,
)


# =========================================================
# MANUAL GROUND-TRUTH LABELLING
# =========================================================

st.write(
    "## 🏷️ Manual Ground-Truth Labelling"
)

st.write(
    "प्रत्येक claim साठी actual correct status select करा."
)


labels_to_save = []


with st.form(
    key=(
        f"evaluation_form_"
        f"{selected_report_id}"
    )
):
    for claim_index, claim_result in enumerate(
        claim_results,
        start=1,
    ):
        predicted_status = str(
            claim_result.get(
                "status",
                "Unsupported",
            )
        )

        if predicted_status not in STATUS_LABELS:
            predicted_status = "Unsupported"

        claim_text = str(
            claim_result.get(
                "claim",
                "Claim unavailable.",
            )
        )

        existing_expected_status = (
            existing_labels.get(
                claim_index,
                predicted_status,
            )
        )

        if (
            existing_expected_status
            not in STATUS_LABELS
        ):
            existing_expected_status = (
                "Unsupported"
            )

        default_index = STATUS_LABELS.index(
            existing_expected_status
        )

        with st.container(
            border=True
        ):
            st.write(
                f"### Claim {claim_index}"
            )

            st.write(claim_text)

            st.write(
                f"**System Predicted Status:** "
                f"{predicted_status}"
            )

            st.write(
                f"**System Confidence:** "
                f"{claim_result.get('confidence_score', 0)}%"
            )

            with st.expander(
                "View explanation and evidence"
            ):
                st.write(
                    "**Explanation:**"
                )

                st.write(
                    claim_result.get(
                        "explanation",
                        "Explanation unavailable.",
                    )
                )

                st.write(
                    "**Supporting Evidence:**"
                )

                st.write(
                    claim_result.get(
                        "supporting_evidence",
                        "Evidence unavailable.",
                    )
                )

            expected_status = st.selectbox(
                label=(
                    f"Correct Expected Status "
                    f"for Claim {claim_index}"
                ),
                options=list(
                    STATUS_LABELS
                ),
                index=default_index,
                key=(
                    f"expected_status_"
                    f"{selected_report_id}_"
                    f"{claim_index}"
                ),
            )

            labels_to_save.append(
                {
                    "claim_index": claim_index,
                    "claim_text": claim_text,
                    "predicted_status": (
                        predicted_status
                    ),
                    "expected_status": (
                        expected_status
                    ),
                }
            )

    confirm_labels = st.checkbox(
        "I checked these claims using trusted evidence"
    )

    save_labels_button = st.form_submit_button(
        label="💾 Save Ground-Truth Labels",
        use_container_width=True,
        type="primary",
    )


if save_labels_button:
    if not confirm_labels:
        st.error(
            "Please confirm that you checked the claims "
            "using trusted evidence."
        )

    else:
        try:
            saved_count = save_ground_truth_labels(
                user_id=user_id,
                verification_id=selected_report_id,
                labels=labels_to_save,
            )

            st.success(
                f"{saved_count} claim labels saved successfully."
            )

        except Exception as error:
            st.error(
                f"Unable to save evaluation labels: {error}"
            )


st.divider()


# =========================================================
# EVALUATION SCOPE
# =========================================================

st.write(
    "## 📊 Performance Metrics"
)

evaluation_scope = st.radio(
    label="Select evaluation scope",
    options=[
        "Selected Report",
        "All My Evaluated Reports",
    ],
    horizontal=True,
)


if evaluation_scope == "Selected Report":
    evaluation_rows = get_evaluation_rows(
        user_id=user_id,
        verification_id=selected_report_id,
    )

else:
    evaluation_rows = get_evaluation_rows(
        user_id=user_id,
    )


if not evaluation_rows:
    st.info(
        "No manually labelled evaluation data is available. "
        "Select correct statuses and save the labels first."
    )

else:
    metrics = calculate_evaluation_metrics(
        evaluation_rows
    )

    (
        accuracy_column,
        precision_column,
        recall_column,
        f1_column,
    ) = st.columns(4)


    with accuracy_column:
        st.metric(
            label="Accuracy",
            value=f"{metrics['accuracy']:.2f}%",
        )


    with precision_column:
        st.metric(
            label="Macro Precision",
            value=f"{metrics['precision']:.2f}%",
        )


    with recall_column:
        st.metric(
            label="Macro Recall",
            value=f"{metrics['recall']:.2f}%",
        )


    with f1_column:
        st.metric(
            label="Macro F1 Score",
            value=f"{metrics['f1_score']:.2f}%",
        )


    st.write(
        f"**Correct Predictions:** "
        f"{metrics['correct_predictions']} "
        f"out of {metrics['total_claims']}"
    )

    st.progress(
        metrics["accuracy"] / 100
    )

    st.divider()

    # -----------------------------------------------------
    # CONFUSION MATRIX
    # -----------------------------------------------------

    st.write(
        "### Confusion Matrix"
    )

    confusion_dataframe = pd.DataFrame(
        metrics["confusion_matrix"]
    )

    st.dataframe(
        confusion_dataframe,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Rows represent actual expected statuses. "
        "Columns represent TrustGuard AI predictions."
    )

    st.divider()

    # -----------------------------------------------------
    # PER-CLASS METRICS
    # -----------------------------------------------------

    st.write(
        "### Status-wise Performance"
    )

    per_class_dataframe = pd.DataFrame(
        metrics["per_class_metrics"]
    )

    st.dataframe(
        per_class_dataframe,
        use_container_width=True,
        hide_index=True,
        column_config={
            "status": "Verification Status",
            "precision": (
                st.column_config.ProgressColumn(
                    "Precision",
                    min_value=0,
                    max_value=100,
                    format="%.2f%%",
                )
            ),
            "recall": (
                st.column_config.ProgressColumn(
                    "Recall",
                    min_value=0,
                    max_value=100,
                    format="%.2f%%",
                )
            ),
            "f1_score": (
                st.column_config.ProgressColumn(
                    "F1 Score",
                    min_value=0,
                    max_value=100,
                    format="%.2f%%",
                )
            ),
            "support": "Actual Claim Count",
        },
    )

    st.divider()

    # -----------------------------------------------------
    # LABELLED CLAIMS
    # -----------------------------------------------------

    st.write(
        "### Evaluated Claims"
    )

    evaluation_dataframe = pd.DataFrame(
        evaluation_rows
    )

    st.dataframe(
        evaluation_dataframe[
            [
                "verification_id",
                "claim_index",
                "claim_text",
                "predicted_status",
                "expected_status",
                "updated_at",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "verification_id": "Report ID",
            "claim_index": "Claim Number",
            "claim_text": "Claim",
            "predicted_status": "Predicted Status",
            "expected_status": "Correct Status",
            "updated_at": "Evaluated At",
        },
    )


# =========================================================
# DELETE CURRENT REPORT EVALUATION
# =========================================================

st.divider()

with st.expander(
    "🗑️ Delete Selected Report Evaluation"
):
    st.warning(
        "This deletes only manually saved evaluation labels. "
        "The original verification report will remain saved."
    )

    delete_confirmation = st.checkbox(
        "I confirm that I want to delete these evaluation labels",
        key=(
            f"delete_evaluation_confirmation_"
            f"{selected_report_id}"
        ),
    )

    delete_button = st.button(
        label="Delete Evaluation Labels",
        use_container_width=True,
        disabled=not delete_confirmation,
    )

    if delete_button:
        deleted = delete_report_evaluation(
            user_id=user_id,
            verification_id=selected_report_id,
        )

        if deleted:
            st.success(
                "Evaluation labels deleted successfully."
            )

            st.rerun()

        else:
            st.info(
                "No evaluation labels were found "
                "for this report."
            )