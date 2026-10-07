from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.database_manager import (
    get_verification_details,
    get_verification_history,
)
from modules.evaluation_manager import (
    STATUS_LABELS,
    calculate_evaluation_metrics,
    delete_report_evaluation,
    get_evaluation_rows,
    get_report_evaluation_labels,
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


# =========================================================
# GET SUPABASE SESSION
# =========================================================

user_id = st.session_state.get(
    "user_id"
)

username = st.session_state.get(
    "username",
    "User",
)

user_email = st.session_state.get(
    "user_email",
    "",
)

access_token = st.session_state.get(
    "access_token",
    "",
)

refresh_token = st.session_state.get(
    "refresh_token",
    "",
)


# =========================================================
# SESSION VALIDATION
# =========================================================

if not user_id:

    st.error(
        "Supabase user session is invalid. "
        "Please logout and login again."
    )

    st.stop()


if not access_token:

    st.error(
        "Supabase access token is missing. "
        "Please logout and login again."
    )

    st.stop()


if not refresh_token:

    st.error(
        "Supabase refresh token is missing. "
        "Please logout and login again."
    )

    st.stop()


# =========================================================
# HEADER
# =========================================================

st.title(
    "📈 TrustGuard AI Evaluation Dashboard"
)

st.write(
    f"Logged in as **{username}**"
)

if user_email:

    st.caption(
        f"Email: {user_email}"
    )


st.write(
    "Compare TrustGuard AI's predicted claim statuses "
    "with manually checked ground-truth statuses."
)



st.divider()


# =========================================================
# LOAD USER VERIFICATION HISTORY
# =========================================================

try:

    history_records = (
        get_verification_history(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            limit=100,
        )
    )

except Exception as error:

    st.error(
        "Unable to load verification history."
    )

    st.code(
        str(error)
    )

    st.stop()


if not history_records:

    st.info(
        "No verification reports are available. "
        "First generate and save a verification report."
    )

    st.stop()


# =========================================================
# REPORT SELECTION
# =========================================================

report_options = {}


for record in history_records:

    report_id = record.get(
        "id"
    )

    question = str(
        record.get(
            "question",
            "Question unavailable",
        )
    )

    score = record.get(
        "overall_score",
        0,
    )

    report_label = (
        f"Report #{report_id} | "
        f"{question[:75]} | "
        f"Score: {score}%"
    )

    report_options[
        report_label
    ] = report_id


selected_report_label = st.selectbox(
    label="Select verification report",
    options=list(
        report_options.keys()
    ),
)


selected_report_id = (
    report_options[
        selected_report_label
    ]
)


# =========================================================
# LOAD SELECTED REPORT
# =========================================================

try:

    selected_report = (
        get_verification_details(
            record_id=int(
                selected_report_id
            ),

            # UUID direct
            user_id=user_id,

            access_token=access_token,

            refresh_token=refresh_token,
        )
    )

except Exception as error:

    st.error(
        "Unable to load selected report."
    )

    st.code(
        str(error)
    )

    st.stop()


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
        "Selected verification report does not contain "
        "claim results."
    )

    st.stop()


# =========================================================
# REPORT SUMMARY
# =========================================================

st.write(
    "## 📄 Selected Verification Report"
)


(
    report_column,
    claim_column,
    score_column,
) = st.columns(3)


with report_column:

    st.metric(
        label="Report ID",
        value=selected_report_id,
    )


with claim_column:

    st.metric(
        label="Total Claims",
        value=len(
            claim_results
        ),
    )


with score_column:

    st.metric(
        label="Trust Score",
        value=(
            f"{selected_report.get('overall_trust_score', 0)}%"
        ),
    )


st.write(
    "### ❓ Question"
)

st.info(
    selected_report.get(
        "question",
        "Question unavailable.",
    )
)


selected_llm = selected_report.get(
    "selected_llm",
    "Unknown",
)

st.caption(
    f"Selected LLM: {selected_llm}"
)

st.divider()


# =========================================================
# LOAD EXISTING EVALUATION LABELS
# =========================================================

try:

    existing_labels = (
        get_report_evaluation_labels(
            user_id=user_id,
            verification_id=int(
                selected_report_id
            ),
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )

except Exception as error:

    st.error(
        "Unable to load saved evaluation labels."
    )

    st.code(
        str(error)
    )

    st.stop()


# =========================================================
# MANUAL GROUND TRUTH
# =========================================================

st.write(
    "## 🏷️ Manual Ground-Truth Labelling"
)




labels_to_save = []


with st.form(
    key=(
        f"evaluation_form_"
        f"{selected_report_id}"
    )
):

    for (
        claim_index,
        claim_result,
    ) in enumerate(
        claim_results,
        start=1,
    ):

        predicted_status = str(
            claim_result.get(
                "status",
                "Unsupported",
            )
        )

        if (
            predicted_status
            not in STATUS_LABELS
        ):

            predicted_status = (
                "Unsupported"
            )


        claim_text = str(
            claim_result.get(
                "claim",
                "Claim unavailable.",
            )
        )


        confidence_score = (
            claim_result.get(
                "confidence_score",
                0,
            )
        )


        explanation = (
            claim_result.get(
                "explanation",
                "Explanation unavailable.",
            )
        )


        supporting_evidence = (
            claim_result.get(
                "supporting_evidence",
                "Evidence unavailable.",
            )
        )


        # Saved label if available.
        # Otherwise predicted status is only the
        # initial UI selection.
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


        default_index = (
            list(
                STATUS_LABELS
            ).index(
                existing_expected_status
            )
        )


        with st.container(
            border=True
        ):

            st.write(
                f"### Claim {claim_index}"
            )

            st.write(
                claim_text
            )


            # =============================================
            # PREDICTED STATUS
            # =============================================

            if predicted_status == "Verified":

                st.success(
                    f"System Prediction: "
                    f"✅ {predicted_status}"
                )


            elif (
                predicted_status
                == "Partially Verified"
            ):

                st.warning(
                    f"System Prediction: "
                    f"⚠️ {predicted_status}"
                )


            elif predicted_status == "Incorrect":

                st.error(
                    f"System Prediction: "
                    f"❌ {predicted_status}"
                )


            else:

                st.info(
                    f"System Prediction: "
                    f"❔ {predicted_status}"
                )


            st.write(
                f"**System Confidence:** "
                f"{confidence_score}%"
            )


            # =============================================
            # EVIDENCE
            # =============================================

            with st.expander(
                "View explanation and evidence"
            ):

                st.write(
                    "**Explanation:**"
                )

                st.write(
                    explanation
                )

                st.write(
                    "**Selected Supporting Evidence:**"
                )

                st.write(
                    supporting_evidence
                )


                retrieved_evidence = (
                    claim_result.get(
                        "evidence",
                        [],
                    )
                )


                if retrieved_evidence:

                    st.write(
                        "**Retrieved Sources:**"
                    )


                    for evidence_number, evidence in enumerate(
                        retrieved_evidence[
                            :5
                        ],
                        start=1,
                    ):

                        source_type = (
                            evidence.get(
                                "source_type",
                                "pdf",
                            )
                        )


                        document = (
                            evidence.get(
                                "document",
                                "Unknown source",
                            )
                        )


                        if source_type == "web":

                            st.write(
                                f"{evidence_number}. "
                                f"🌐 {document}"
                            )

                        else:

                            page = evidence.get(
                                "page",
                                "Unknown",
                            )

                            st.write(
                                f"{evidence_number}. "
                                f"📄 {document} "
                                f"— Page {page}"
                            )


            # =============================================
            # EXPECTED STATUS
            # =============================================

            expected_status = st.selectbox(
                label=(
                    "Correct Expected Status "
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
                    "claim_index": (
                        claim_index
                    ),

                    "claim_text": (
                        claim_text
                    ),

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


    save_labels_button = (
        st.form_submit_button(
            label=(
                "💾 Save Ground-Truth Labels"
            ),
            use_container_width=True,
            type="primary",
        )
    )


# =========================================================
# SAVE LABELS TO SUPABASE
# =========================================================

if save_labels_button:

    if not confirm_labels:

        st.error(
            "Please confirm that you checked "
            "the claims using trusted evidence."
        )

    else:

        try:

            saved_count = (
                save_ground_truth_labels(
                    # UUID direct
                    user_id=user_id,

                    verification_id=int(
                        selected_report_id
                    ),

                    labels=labels_to_save,

                    access_token=(
                        access_token
                    ),

                    refresh_token=(
                        refresh_token
                    ),
                )
            )


            st.success(
                f"{saved_count} evaluation labels "
                f"saved to Supabase successfully."
            )

            st.rerun()


        except Exception as error:

            st.error(
                "Unable to save evaluation labels."
            )

            st.code(
                str(error)
            )


st.divider()


# =========================================================
# PERFORMANCE METRICS
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


try:

    if evaluation_scope == "Selected Report":

        evaluation_rows = (
            get_evaluation_rows(
                user_id=user_id,
                verification_id=int(
                    selected_report_id
                ),
                access_token=(
                    access_token
                ),
                refresh_token=(
                    refresh_token
                ),
            )
        )

    else:

        evaluation_rows = (
            get_evaluation_rows(
                user_id=user_id,
                access_token=(
                    access_token
                ),
                refresh_token=(
                    refresh_token
                ),
            )
        )


except Exception as error:

    st.error(
        "Unable to load evaluation data."
    )

    st.code(
        str(error)
    )

    st.stop()


# =========================================================
# DISPLAY METRICS
# =========================================================

if not evaluation_rows:

    st.info(
        "No manually evaluated claims are available. "
        "Save Ground-Truth Labels first."
    )


else:

    metrics = (
        calculate_evaluation_metrics(
            evaluation_rows
        )
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
            value=(
                f"{metrics['accuracy']:.2f}%"
            ),
        )


    with precision_column:

        st.metric(
            label="Macro Precision",
            value=(
                f"{metrics['precision']:.2f}%"
            ),
        )


    with recall_column:

        st.metric(
            label="Macro Recall",
            value=(
                f"{metrics['recall']:.2f}%"
            ),
        )


    with f1_column:

        st.metric(
            label="Macro F1 Score",
            value=(
                f"{metrics['f1_score']:.2f}%"
            ),
        )


    st.write(
        f"**Correct Predictions:** "
        f"{metrics['correct_predictions']} "
        f"out of "
        f"{metrics['total_claims']}"
    )


    st.progress(
        metrics[
            "accuracy"
        ]
        / 100
    )


    st.divider()


    # =====================================================
    # CONFUSION MATRIX
    # =====================================================

    st.write(
        "### 🔢 Confusion Matrix"
    )


    confusion_dataframe = pd.DataFrame(
        metrics[
            "confusion_matrix"
        ]
    )


    st.dataframe(
        confusion_dataframe,
        use_container_width=True,
        hide_index=True,
    )


    st.caption(
        "Rows = actual manually assigned status. "
        "Columns = TrustGuard AI predicted status."
    )


    st.divider()


    # =====================================================
    # STATUS-WISE METRICS
    # =====================================================

    st.write(
        "### 📋 Status-wise Performance"
    )


    per_class_dataframe = (
        pd.DataFrame(
            metrics[
                "per_class_metrics"
            ]
        )
    )


    st.dataframe(
        per_class_dataframe,
        use_container_width=True,
        hide_index=True,

        column_config={
            "status": (
                "Verification Status"
            ),

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

            "support": (
                "Actual Claim Count"
            ),
        },
    )


    st.divider()


    # =====================================================
    # EVALUATED CLAIMS
    # =====================================================

    st.write(
        "### 📝 Evaluated Claims"
    )


    evaluation_dataframe = (
        pd.DataFrame(
            evaluation_rows
        )
    )


    desired_columns = [
        "verification_id",
        "claim_index",
        "claim_text",
        "predicted_status",
        "expected_status",
        "updated_at",
    ]


    available_columns = [
        column
        for column
        in desired_columns
        if column
        in evaluation_dataframe.columns
    ]


    st.dataframe(
        evaluation_dataframe[
            available_columns
        ],
        use_container_width=True,
        hide_index=True,

        column_config={
            "verification_id": (
                "Report ID"
            ),

            "claim_index": (
                "Claim Number"
            ),

            "claim_text": (
                "Claim"
            ),

            "predicted_status": (
                "AI Prediction"
            ),

            "expected_status": (
                "Correct Status"
            ),

            "updated_at": (
                "Evaluated At"
            ),
        },
    )


# =========================================================
# DELETE EVALUATION LABELS
# =========================================================

st.divider()


with st.expander(
    "🗑️ Delete Selected Report Evaluation"
):

    st.warning(
        "This deletes only the manually saved "
        "evaluation labels. The original verification "
        "report remains saved."
    )


    delete_confirmation = st.checkbox(
        label=(
            "I confirm that I want to delete "
            "these evaluation labels"
        ),

        key=(
            "delete_evaluation_"
            f"{selected_report_id}"
        ),
    )


    delete_button = st.button(
        label="Delete Evaluation Labels",
        use_container_width=True,
        disabled=(
            not delete_confirmation
        ),
    )


    if delete_button:

        try:

            deleted = (
                delete_report_evaluation(
                    # UUID direct
                    user_id=user_id,

                    verification_id=int(
                        selected_report_id
                    ),

                    access_token=(
                        access_token
                    ),

                    refresh_token=(
                        refresh_token
                    ),
                )
            )


            if deleted:

                st.success(
                    "Evaluation labels deleted "
                    "successfully."
                )

                st.rerun()


            else:

                st.info(
                    "No evaluation labels were "
                    "found for this report."
                )


        except Exception as error:

            st.error(
                "Unable to delete evaluation labels."
            )

            st.code(
                str(error)
            )


# =========================================================
# SECURITY NOTE
# =========================================================

st.divider()


st.info(
    "Evaluation data is stored in Supabase Cloud "
    "and protected using the authenticated user's "
    "UUID and Row Level Security."
)