import json

import streamlit as st

from modules.database_manager import (
    delete_verification,
    get_verification_details,
    get_verification_history,
    init_database,
)


st.set_page_config(
    page_title="My Verification History",
    page_icon="📚",
    layout="wide",
)

init_database()


# =========================================================
# LOGIN PROTECTION
# =========================================================

if not st.session_state.get(
    "logged_in",
    False,
):
    st.warning(
        "Please login from the main TrustGuard AI page "
        "to view verification history."
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
        "User session is invalid. Please logout and login again."
    )

    st.stop()


# =========================================================
# PAGE HEADER
# =========================================================

st.title("📚 My Verification History")

st.write(
    f"Logged in as **{username}**"
)

st.write(
    "Only verification reports created using your account "
    "are displayed here."
)

st.divider()


# =========================================================
# LOAD USER HISTORY
# =========================================================

history_records = get_verification_history(
    user_id=int(user_id),
    limit=100,
)


if not history_records:
    st.info(
        "You have not generated any verification reports yet."
    )

    st.stop()


st.write("## Recent Verifications")

st.dataframe(
    history_records,
    use_container_width=True,
    hide_index=True,
    column_config={
        "id": "Record ID",
        "created_at": "Generated At",
        "document_name": "Document",
        "question": "Question",
        "overall_score": (
            st.column_config.ProgressColumn(
                "Trust Score",
                min_value=0,
                max_value=100,
                format="%d%%",
            )
        ),
        "trust_level": "Trust Level",
    },
)

st.divider()


# =========================================================
# SELECT REPORT
# =========================================================

record_options = {
    (
        f"Record #{record['id']} | "
        f"{record['question'][:70]} | "
        f"{record['overall_score']}%"
    ): record["id"]
    for record in history_records
}


selected_label = st.selectbox(
    "Select a verification report",
    options=list(
        record_options.keys()
    ),
)


selected_record_id = record_options[
    selected_label
]


report = get_verification_details(
    record_id=int(selected_record_id),
    user_id=int(user_id),
)


if report is None:
    st.error(
        "The selected report was not found or "
        "does not belong to your account."
    )

    st.stop()


# =========================================================
# REPORT SUMMARY
# =========================================================

st.write("## Selected Verification Report")

document_column, score_column, level_column = (
    st.columns(3)
)


with document_column:
    st.metric(
        "Document",
        report.get(
            "document_name",
            "Unknown",
        ),
    )


with score_column:
    st.metric(
        "Overall Trust Score",
        f"{report.get('overall_trust_score', 0)}%",
    )


with level_column:
    st.metric(
        "Trust Level",
        report.get(
            "trust_level",
            "Unknown",
        ),
    )


st.write("### ❓ Question")

st.info(
    report.get(
        "question",
        "Question unavailable.",
    )
)


st.write("### 🤖 Original AI Answer")

st.success(
    report.get(
        "original_ai_answer",
        "AI answer unavailable.",
    )
)


st.write("### ✅ Final Verified Response")

st.write(
    report.get(
        "final_verified_response",
        "Verified response unavailable.",
    )
)

st.divider()


# =========================================================
# CLAIM RESULTS
# =========================================================

st.write("## 🔎 Claim Verification Results")

claim_results = report.get(
    "claim_results",
    [],
)


if not claim_results:
    st.warning(
        "No claim verification results are available."
    )


for claim_number, result in enumerate(
    claim_results,
    start=1,
):
    status = result.get(
        "status",
        "Unsupported",
    )

    try:
        confidence_score = int(
            result.get(
                "confidence_score",
                0,
            )
        )
    except (TypeError, ValueError):
        confidence_score = 0

    confidence_score = max(
        0,
        min(100, confidence_score),
    )

    with st.container(border=True):
        st.write(
            f"### Claim {claim_number}"
        )

        st.write(
            result.get(
                "claim",
                "Claim unavailable.",
            )
        )

        if status == "Verified":
            st.success(
                f"✅ {status} — {confidence_score}%"
            )

        elif status == "Partially Verified":
            st.warning(
                f"⚠️ {status} — {confidence_score}%"
            )

        elif status == "Incorrect":
            st.error(
                f"❌ {status} — {confidence_score}%"
            )

        else:
            st.info(
                f"❔ {status} — {confidence_score}%"
            )

        st.progress(
            confidence_score / 100
        )

        st.write("**Explanation:**")

        st.write(
            result.get(
                "explanation",
                "Explanation unavailable.",
            )
        )

        st.write("**Supporting Evidence:**")

        st.write(
            result.get(
                "supporting_evidence",
                "Evidence unavailable.",
            )
        )


st.divider()


# =========================================================
# DOWNLOAD AND DELETE
# =========================================================

json_report = json.dumps(
    report,
    indent=4,
    ensure_ascii=False,
)


download_column, delete_column = (
    st.columns(2)
)


with download_column:
    st.download_button(
        label="📥 Download Selected JSON Report",
        data=json_report,
        file_name=(
            f"trustguard_report_"
            f"{selected_record_id}.json"
        ),
        mime="application/json",
        use_container_width=True,
        on_click="ignore",
    )


with delete_column:
    delete_confirmation = st.checkbox(
        "I confirm that I want to delete this report",
        key=(
            f"delete_confirmation_"
            f"{selected_record_id}"
        ),
    )

    delete_button = st.button(
        "🗑️ Delete Selected Report",
        use_container_width=True,
        disabled=not delete_confirmation,
    )

    if delete_button:
        deleted = delete_verification(
            record_id=int(
                selected_record_id
            ),
            user_id=int(user_id),
        )

        if deleted:
            st.success(
                "Verification report deleted successfully."
            )

            st.rerun()

        else:
            st.error(
                "Unable to delete this report."
            )