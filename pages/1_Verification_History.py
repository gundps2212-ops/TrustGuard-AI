import json

import streamlit as st

from modules.database_manager import (
    delete_verification,
    get_verification_details,
    get_verification_history,
    init_database,
)


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="My Verification History",
    page_icon="📚",
    layout="wide",
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

# Supabase version मध्ये ही compatibility function आहे.
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


# =========================================================
# GET SUPABASE SESSION INFORMATION
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

user_role = st.session_state.get(
    "user_role",
    "user",
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
        "User session is invalid. "
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
# PAGE HEADER
# =========================================================

st.title(
    "📚 My Verification History"
)

st.write(
    f"Logged in as **{username}**"
)

if user_email:
    st.caption(
        f"Email: {user_email}"
    )

st.caption(
    f"Account Role: {str(user_role).title()}"
)

st.write(
    "Only verification reports created using "
    "your account are displayed here."
)

st.divider()


# =========================================================
# LOAD VERIFICATION HISTORY FROM SUPABASE
# =========================================================

try:
    history_records = get_verification_history(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        limit=100,
    )

except Exception as error:
    st.error(
        "Unable to load verification history."
    )

    st.code(
        str(error)
    )

    st.info(
        "Please logout, login again and retry."
    )

    st.stop()


# =========================================================
# EMPTY HISTORY
# =========================================================

if not history_records:
    st.info(
        "You have not generated any verification "
        "reports yet."
    )

    st.write(
        "Go to the TrustGuard AI main page, "
        "verify an AI answer and the report "
        "will appear here."
    )

    st.stop()


# =========================================================
# HISTORY SUMMARY
# =========================================================

st.write(
    "## 📊 History Summary"
)


total_reports = len(
    history_records
)


trust_scores = []

for record in history_records:
    try:
        score = int(
            record.get(
                "overall_score",
                0,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        score = 0

    trust_scores.append(
        score
    )


if trust_scores:
    average_score = sum(
        trust_scores
    ) / len(
        trust_scores
    )

    highest_score = max(
        trust_scores
    )

    lowest_score = min(
        trust_scores
    )

else:
    average_score = 0
    highest_score = 0
    lowest_score = 0


(
    total_column,
    average_column,
    highest_column,
    lowest_column,
) = st.columns(4)


with total_column:
    st.metric(
        label="Total Reports",
        value=total_reports,
    )


with average_column:
    st.metric(
        label="Average Trust Score",
        value=f"{average_score:.2f}%",
    )


with highest_column:
    st.metric(
        label="Highest Score",
        value=f"{highest_score}%",
    )


with lowest_column:
    st.metric(
        label="Lowest Score",
        value=f"{lowest_score}%",
    )


st.divider()


# =========================================================
# HISTORY TABLE
# =========================================================

st.write(
    "## 🗂️ Recent Verifications"
)


st.dataframe(
    history_records,
    use_container_width=True,
    hide_index=True,
    column_config={
        "id": "Record ID",

        "created_at": (
            "Generated At"
        ),

        "document_name": (
            "Document"
        ),

        "question": (
            "Question"
        ),

        "overall_score": (
            st.column_config.ProgressColumn(
                "Trust Score",
                min_value=0,
                max_value=100,
                format="%d%%",
            )
        ),

        "trust_level": (
            "Trust Level"
        ),
    },
)


st.divider()


# =========================================================
# CREATE REPORT OPTIONS
# =========================================================

record_options = {}


for record in history_records:

    record_id = record.get(
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

    document_name = str(
        record.get(
            "document_name",
            "Unknown document",
        )
    )

    short_question = question[:70]

    label = (
        f"Report #{record_id} | "
        f"{short_question} | "
        f"{score}% | "
        f"{document_name}"
    )

    record_options[
        label
    ] = record_id


# =========================================================
# SELECT REPORT
# =========================================================

st.write(
    "## 🔎 View Verification Report"
)


selected_label = st.selectbox(
    label="Select a verification report",
    options=list(
        record_options.keys()
    ),
)


selected_record_id = (
    record_options[
        selected_label
    ]
)


# =========================================================
# LOAD REPORT DETAILS
# =========================================================

try:
    report = get_verification_details(
        record_id=int(
            selected_record_id
        ),

        # IMPORTANT:
        # Supabase user_id UUID आहे,
        # त्यामुळे int(user_id) करू नका.
        user_id=user_id,

        access_token=access_token,

        refresh_token=refresh_token,
    )

except Exception as error:
    st.error(
        "Unable to load the selected report."
    )

    st.code(
        str(error)
    )

    st.stop()


if report is None:
    st.error(
        "The selected verification report "
        "was not found or does not belong "
        "to your account."
    )

    st.stop()


st.divider()


# =========================================================
# REPORT INFORMATION
# =========================================================

st.write(
    "## 📄 Selected Verification Report"
)


report_document = report.get(
    "document_name",
    "Unknown",
)

report_score = report.get(
    "overall_trust_score",
    0,
)

report_trust_level = report.get(
    "trust_level",
    "Unknown",
)


(
    document_column,
    score_column,
    trust_column,
) = st.columns(3)


with document_column:
    st.metric(
        label="Document",
        value=str(
            report_document
        ),
    )


with score_column:
    st.metric(
        label="Overall Trust Score",
        value=f"{report_score}%",
    )


with trust_column:
    st.metric(
        label="Trust Level",
        value=str(
            report_trust_level
        ),
    )


# =========================================================
# USER / MODEL INFORMATION
# =========================================================

information_column_1, information_column_2 = (
    st.columns(2)
)


with information_column_1:

    generated_by = report.get(
        "generated_by",
        username,
    )

    st.write(
        f"**Generated By:** "
        f"{generated_by}"
    )

    selected_llm = report.get(
        "selected_llm",
        "Unknown",
    )

    st.write(
        f"**Selected LLM:** "
        f"{selected_llm}"
    )


with information_column_2:

    report_email = report.get(
        "user_email",
        user_email,
    )

    if report_email:
        st.write(
            f"**User Email:** "
            f"{report_email}"
        )

    web_enabled = report.get(
        "web_verification_enabled",
        False,
    )

    st.write(
        f"**Web Verification:** "
        f"{'Enabled' if web_enabled else 'Disabled'}"
    )


st.divider()


# =========================================================
# QUESTION
# =========================================================

st.write(
    "### ❓ User Question"
)

st.info(
    report.get(
        "question",
        "Question unavailable.",
    )
)


# =========================================================
# ORIGINAL AI ANSWER
# =========================================================

st.write(
    "### 🤖 Original AI Answer"
)

st.write(
    report.get(
        "original_ai_answer",
        "AI answer unavailable.",
    )
)


# =========================================================
# GEMINI / LLAMA COMPARISON
# =========================================================

comparison_enabled = report.get(
    "llm_comparison_enabled",
    False,
)


if comparison_enabled:

    with st.expander(
        "🤖 View Gemini and Llama Responses"
    ):

        gemini_column, llama_column = (
            st.columns(2)
        )


        with gemini_column:

            st.write(
                "### Gemini"
            )

            st.write(
                report.get(
                    "gemini_answer",
                    "Gemini answer unavailable.",
                )
            )


        with llama_column:

            st.write(
                "### Llama"
            )

            st.write(
                report.get(
                    "llama_answer",
                    "Llama answer unavailable.",
                )
            )


# =========================================================
# FINAL VERIFIED RESPONSE
# =========================================================

st.write(
    "### ✅ Final Verified Response"
)

final_verified_response = report.get(
    "final_verified_response",
    "Verified response unavailable.",
)


if report_score >= 80:

    st.success(
        final_verified_response
    )

elif report_score >= 50:

    st.warning(
        final_verified_response
    )

else:

    st.error(
        final_verified_response
    )


st.divider()


# =========================================================
# CLAIM RESULTS
# =========================================================

st.write(
    "## 🔎 Claim Verification Results"
)


claim_results = report.get(
    "claim_results",
    [],
)


if not claim_results:

    st.warning(
        "No claim verification results "
        "are available in this report."
    )


else:

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

        except (
            TypeError,
            ValueError,
        ):
            confidence_score = 0


        confidence_score = max(
            0,
            min(
                100,
                confidence_score,
            ),
        )


        claim_text = result.get(
            "claim",
            "Claim unavailable.",
        )


        explanation = result.get(
            "explanation",
            "Explanation unavailable.",
        )


        supporting_evidence = result.get(
            "supporting_evidence",
            "",
        )


        retrieved_evidence = result.get(
            "evidence",
            [],
        )


        with st.container(
            border=True
        ):

            st.write(
                f"### Claim {claim_number}"
            )

            st.write(
                claim_text
            )


            # ---------------------------------------------
            # STATUS
            # ---------------------------------------------

            status_message = (
                f"{status} — "
                f"{confidence_score}%"
            )


            if status == "Verified":

                st.success(
                    f"✅ {status_message}"
                )


            elif status == "Partially Verified":

                st.warning(
                    f"⚠️ {status_message}"
                )


            elif status == "Incorrect":

                st.error(
                    f"❌ {status_message}"
                )


            else:

                st.info(
                    f"❔ {status_message}"
                )


            st.progress(
                confidence_score / 100
            )


            # ---------------------------------------------
            # EXPLANATION
            # ---------------------------------------------

            st.write(
                "#### Explanation"
            )

            st.write(
                explanation
            )


            # ---------------------------------------------
            # SUPPORTING EVIDENCE
            # ---------------------------------------------

            st.write(
                "#### Supporting Evidence"
            )

            if supporting_evidence:

                st.write(
                    supporting_evidence
                )

            else:

                st.info(
                    "No supporting evidence "
                    "was selected."
                )


            # ---------------------------------------------
            # RETRIEVED EVIDENCE
            # ---------------------------------------------

            if retrieved_evidence:

                st.write(
                    "#### Retrieved Evidence Sources"
                )


                for evidence_number, evidence in enumerate(
                    retrieved_evidence,
                    start=1,
                ):

                    source_type = evidence.get(
                        "source_type",
                        "pdf",
                    )


                    source_document = evidence.get(
                        "document",
                        "Unknown source",
                    )


                    evidence_text = evidence.get(
                        "text",
                        "Evidence text unavailable.",
                    )


                    try:
                        similarity_score = float(
                            evidence.get(
                                "similarity",
                                0,
                            )
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        similarity_score = 0.0


                    # =====================================
                    # WEB SOURCE
                    # =====================================

                    if source_type == "web":

                        source_domain = evidence.get(
                            "domain",
                            "Unknown domain",
                        )

                        source_url = evidence.get(
                            "url",
                            "",
                        )

                        relevance_level = evidence.get(
                            "relevance_level",
                            "Unknown",
                        )


                        expander_title = (
                            f"🌐 Web Evidence "
                            f"{evidence_number} "
                            f"— {source_document} "
                            f"— {similarity_score:.4f}"
                        )


                        with st.expander(
                            expander_title
                        ):

                            st.write(
                                f"**Source:** "
                                f"{source_document}"
                            )

                            st.write(
                                f"**Domain:** "
                                f"{source_domain}"
                            )

                            st.write(
                                f"**Relevance Score:** "
                                f"{similarity_score:.4f}"
                            )

                            st.write(
                                f"**Relevance Level:** "
                                f"{relevance_level}"
                            )

                            if source_url:

                                st.link_button(
                                    label=(
                                        "🔗 Open Web Source"
                                    ),
                                    url=source_url,
                                )


                            st.write(
                                "**Evidence Text:**"
                            )

                            st.write(
                                evidence_text
                            )


                    # =====================================
                    # PDF SOURCE
                    # =====================================

                    else:

                        source_page = evidence.get(
                            "page",
                            "Unknown",
                        )

                        source_chunk = evidence.get(
                            "chunk_number",
                            "Unknown",
                        )


                        expander_title = (
                            f"📄 PDF Evidence "
                            f"{evidence_number} "
                            f"— {source_document} "
                            f"— Page {source_page}"
                        )


                        with st.expander(
                            expander_title
                        ):

                            st.write(
                                f"**Document:** "
                                f"{source_document}"
                            )

                            st.write(
                                f"**Page:** "
                                f"{source_page}"
                            )

                            st.write(
                                f"**Chunk Number:** "
                                f"{source_chunk}"
                            )

                            st.write(
                                f"**Similarity Score:** "
                                f"{similarity_score:.4f}"
                            )

                            st.write(
                                "**Evidence Text:**"
                            )

                            st.write(
                                evidence_text
                            )


st.divider()


# =========================================================
# DOWNLOAD REPORT
# =========================================================

st.write(
    "## 📥 Download Selected Report"
)


json_report = json.dumps(
    report,
    indent=4,
    ensure_ascii=False,
)


st.download_button(
    label="📄 Download JSON Report",
    data=json_report,
    file_name=(
        f"trustguard_report_"
        f"{selected_record_id}.json"
    ),
    mime="application/json",
    use_container_width=True,
    on_click="ignore",
)


st.divider()


# =========================================================
# DELETE REPORT
# =========================================================

with st.expander(
    "🗑️ Delete Verification Report"
):

    st.warning(
        "Deleting this report is permanent "
        "and cannot be undone."
    )


    delete_confirmation = st.checkbox(
        label=(
            "I confirm that I want to "
            "delete this verification report."
        ),
        key=(
            f"delete_confirmation_"
            f"{selected_record_id}"
        ),
    )


    delete_button = st.button(
        label="🗑️ Delete Selected Report",
        use_container_width=True,
        disabled=not delete_confirmation,
        key=(
            f"delete_report_"
            f"{selected_record_id}"
        ),
    )


    if delete_button:

        try:

            deleted = delete_verification(
                record_id=int(
                    selected_record_id
                ),

                # UUID direct वापरायचा
                user_id=user_id,

                access_token=access_token,

                refresh_token=refresh_token,
            )


            if deleted:

                st.success(
                    "Verification report deleted "
                    "successfully."
                )

                st.rerun()


            else:

                st.error(
                    "Unable to delete this report "
                    "or the report does not belong "
                    "to your account."
                )


        except Exception as error:

            st.error(
                "Unable to delete the report."
            )

            st.code(
                str(error)
            )


# =========================================================
# SECURITY NOTE
# =========================================================

st.divider()

st.info(
    "Verification history is protected using "
    "Supabase authentication and Row Level Security. "
    "Only reports accessible to the logged-in account "
    "are shown."
)