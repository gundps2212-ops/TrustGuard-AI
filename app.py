import streamlit as st

from modules.auth_manager import (
    authenticate_user,
    init_auth_database,
    register_user,
)
from modules.claim_extractor import extract_factual_claims
from modules.database_manager import (
    init_database,
    save_verification,
)
from modules.evidence_retriever import (
    build_evidence_index,
    search_evidence,
)
from modules.llm import generate_ai_answer
from modules.llm_comparison import generate_llama_answer
from modules.pdf_reader import extract_multiple_pdfs
from modules.pdf_report_generator import create_pdf_report
from modules.report_generator import (
    build_final_response,
    create_json_report,
    create_report_data,
    create_text_report,
)
from modules.score import (
    calculate_overall_score,
    count_statuses,
    get_trust_level,
)
from modules.verifier import verify_all_claims
from modules.web_retriever import (
    TRUSTED_DOMAIN_GROUPS,
    search_web_evidence,
)


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="TrustGuard AI",
    page_icon="🛡️",
    layout="wide",
)

init_database()
init_auth_database()


# =========================================================
# CONSTANTS
# =========================================================

VALID_STATUSES = {
    "Verified",
    "Partially Verified",
    "Unsupported",
    "Incorrect",
}


# =========================================================
# SESSION STATE
# =========================================================

SESSION_DEFAULTS = {
    "logged_in": False,
    "user_id": None,
    "username": "",
    "user_role": "user",
    "gemini_answer": "",
    "llama_answer": "",
    "generated_question": "",
    "generated_compare_setting": False,
    "selected_model": "Gemini",
    "verification_output": None,
}

for key, default_value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


# =========================================================
# HELPER FUNCTIONS
# =========================================================


def safe_confidence_score(value) -> int:
    """Convert confidence score into an integer from 0 to 100."""

    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 0

    return max(0, min(100, score))



def safe_float(value) -> float:
    """Convert a value safely into float."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0



def normalize_status(status: str) -> str:
    """Return a valid verification status."""

    if status in VALID_STATUSES:
        return status

    return "Unsupported"



def display_verification_status(
    status: str,
    confidence_score: int,
) -> None:
    """Display the verification status."""

    message = f"{status} — Confidence Score: {confidence_score}%"

    if status == "Verified":
        st.success(f"✅ {message}")
    elif status == "Partially Verified":
        st.warning(f"⚠️ {message}")
    elif status == "Incorrect":
        st.error(f"❌ {message}")
    else:
        st.info(f"❔ {message}")



def get_selected_supporting_evidence(result: dict) -> str:
    """
    Return verifier-selected evidence.

    If the verifier returns empty evidence, use the best retrieved evidence.
    """

    supporting_evidence = (
        result.get("supporting_evidence") or ""
    ).strip()

    if supporting_evidence:
        return supporting_evidence

    evidence_items = result.get("evidence", [])

    if evidence_items:
        evidence_text = (
            evidence_items[0].get("text") or ""
        ).strip()

        if evidence_text:
            return evidence_text

    return "No supporting evidence was selected."



def create_pdf_preview(
    page_records: list[dict],
    limit: int = 7000,
) -> str:
    """Create PDF text preview with document and page metadata."""

    preview_parts = []

    for record in page_records:
        document_name = record.get(
            "document",
            "Unknown document",
        )
        page_number = record.get("page", "Unknown")
        page_text = record.get("text", "")

        preview_parts.append(
            f"--- {document_name} | Page {page_number} ---\n"
            f"{page_text}"
        )

    return "\n\n".join(preview_parts)[:limit]



def count_evidence_sources(
    verification_results: list[dict],
) -> tuple[int, int]:
    """Count PDF and web evidence results."""

    pdf_count = 0
    web_count = 0

    for result in verification_results:
        for evidence in result.get("evidence", []):
            if evidence.get("source_type", "pdf") == "web":
                web_count += 1
            else:
                pdf_count += 1

    return pdf_count, web_count



def reset_application() -> None:
    """Clear generated answers and verification results."""

    st.session_state.gemini_answer = ""
    st.session_state.llama_answer = ""
    st.session_state.generated_question = ""
    st.session_state.generated_compare_setting = False
    st.session_state.selected_model = "Gemini"
    st.session_state.verification_output = None



def logout_user() -> None:
    """Clear user session and application state."""

    reset_application()
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""
    st.session_state.user_role = "user"


def handle_application_error(error: Exception) -> None:
    """Display readable API and application errors."""

    error_message = str(error)
    lower_message = error_message.lower()

    if (
        "429" in error_message
        or "quota" in lower_message
        or "too_many_requests" in lower_message
    ):
        st.error("API quota पूर्ण झाली आहे.")
        st.warning(
            "Quota reset झाल्यानंतर पुन्हा प्रयत्न करा. "
            "Generate किंवा Verify button वारंवार click करू नका."
        )
    elif "GROQ_API_KEY" in error_message:
        st.error("Groq API key मिळाली नाही.")
        st.info("`.env` file मध्ये GROQ_API_KEY add करा.")
    elif "TAVILY_API_KEY" in error_message:
        st.error("Tavily API key मिळाली नाही.")
        st.info("`.env` file मध्ये TAVILY_API_KEY add करा.")
    elif "GEMINI_API_KEY" in error_message:
        st.error("Gemini API key मिळाली नाही.")
        st.info("`.env` file मध्ये GEMINI_API_KEY add करा.")
    else:
        st.error(f"Application error: {error_message}")
        st.info(
            "API keys, internet connection, packages आणि "
            "uploaded PDF documents तपासा."
        )


# =========================================================
# AUTHENTICATION PAGE
# =========================================================


def display_authentication_page() -> None:
    """Display login and registration forms."""

    st.title("🛡️ TrustGuard AI")
    st.subheader("Hallucination Detection & Fact Verification")
    st.write(
        "Login करा किंवा नवीन account तयार करून "
        "TrustGuard AI dashboard वापरा."
    )
    st.divider()

    login_tab, register_tab = st.tabs(
        ["🔐 Login", "📝 Register"]
    )

    with login_tab:
        st.write("### Login to your account")

        with st.form(
            "login_form",
            clear_on_submit=False,
        ):
            login_value = st.text_input(
                "Username or Email"
            )
            login_password = st.text_input(
                "Password",
                type="password",
            )
            login_button = st.form_submit_button(
                "Login",
                use_container_width=True,
                type="primary",
            )

        if login_button:
            user = authenticate_user(
                username_or_email=login_value,
                password=login_password,
            )

            if user is None:
                st.error(
                    "Incorrect username, email or password."
                )
            else:
                st.session_state.logged_in = True
                st.session_state.user_id = int(user["id"])
                st.session_state.username = user["username"]
                st.session_state.user_role = user.get(
                       "role",
                    "user",
                )
                st.success("Login successful.")
                st.rerun()

    with register_tab:
        st.write("### Create a new account")

        with st.form(
            "registration_form",
            clear_on_submit=True,
        ):
            register_username = st.text_input(
                "Choose Username"
            )
            register_email = st.text_input(
                "Email Address"
            )
            register_password = st.text_input(
                "Create Password",
                type="password",
            )
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
            )
            register_button = st.form_submit_button(
                "Create Account",
                use_container_width=True,
                type="primary",
            )

        if register_button:
            success, message = register_user(
                username=register_username,
                email=register_email,
                password=register_password,
                confirm_password=confirm_password,
            )

            if success:
                st.success(message)
            else:
                st.error(message)


# =========================================================
# RESULT DISPLAY FUNCTION
# =========================================================


def display_verification_output(output: dict) -> None:
    """Display the complete verification result."""

    st.success("Answer verification completed successfully!")
    st.caption(
        f"Verification saved in your history. "
        f"Record ID: {output['saved_record_id']}"
    )
    st.divider()

    st.write("## 📄 Document and Source Information")

    (
        document_column,
        page_column,
        chunk_column,
        web_column,
    ) = st.columns(4)

    with document_column:
        st.metric(
            "Uploaded Documents",
            len(output["document_names"]),
        )

    with page_column:
        st.metric(
            "Total PDF Pages",
            output["total_page_count"],
        )

    with chunk_column:
        st.metric(
            "Document Chunks",
            output["chunk_count"],
        )

    with web_column:
        st.metric(
            "Web Verification",
            "Enabled"
            if output["use_web_verification"]
            else "Disabled",
        )

    source_column_1, source_column_2 = st.columns(2)

    with source_column_1:
        st.metric(
            "PDF Evidence Results",
            output["pdf_evidence_count"],
        )

    with source_column_2:
        st.metric(
            "Web Evidence Results",
            output["web_evidence_count"],
        )

    st.write("### Uploaded Documents")

    for document_name in output["document_names"]:
        st.write(f"📄 {document_name}")

    if output["use_web_verification"]:
        st.write("### Web Verification Settings")
        st.write(
            f"**Trusted Domain Category:** "
            f"{output['trusted_domain_group']}"
        )
        st.write(
            f"**Minimum Relevance Score:** "
            f"{output['minimum_web_score']:.2f}"
        )

    st.divider()

    st.write("## ❓ User Question")
    st.info(output["question"])

    st.write("## 🤖 Selected AI Answer")
    st.write(
        f"**Selected Model:** {output['selected_model']}"
    )
    st.success(output["ai_answer"])

    if output["comparison_enabled"]:
        with st.expander("🤖 View Gemini and Llama Answers"):
            gemini_column, llama_column = st.columns(2)

            with gemini_column:
                st.write("### Gemini")
                st.write(output["gemini_answer"])

            with llama_column:
                st.write("### Llama")
                st.write(
                    output["llama_answer"]
                    or "Llama answer unavailable."
                )

    st.divider()

    st.write("## 🛡️ Verification Dashboard")

    status_counts = output["status_counts"]

    (
        score_column,
        verified_column,
        partial_column,
        issue_column,
    ) = st.columns(4)

    with score_column:
        st.metric(
            "Overall Trust Score",
            f"{output['overall_score']}%",
        )

    with verified_column:
        st.metric(
            "Verified Claims",
            status_counts["Verified"],
        )

    with partial_column:
        st.metric(
            "Partially Verified",
            status_counts["Partially Verified"],
        )

    with issue_column:
        total_issues = (
            status_counts["Unsupported"]
            + status_counts["Incorrect"]
        )
        st.metric(
            "Unsupported / Incorrect",
            total_issues,
        )

    st.write(f"### Trust Level: {output['trust_level']}")
    st.progress(output["overall_score"] / 100)

    summary_column_1, summary_column_2 = st.columns(2)

    with summary_column_1:
        st.write(
            f"✅ Verified: {status_counts['Verified']}"
        )
        st.write(
            "⚠️ Partially Verified: "
            f"{status_counts['Partially Verified']}"
        )

    with summary_column_2:
        st.write(
            f"❔ Unsupported: {status_counts['Unsupported']}"
        )
        st.write(
            f"❌ Incorrect: {status_counts['Incorrect']}"
        )

    st.divider()

    st.write("## ✅ Final Verified Response")

    if status_counts["Verified"] > 0:
        st.success(output["final_verified_response"])
    elif status_counts["Partially Verified"] > 0:
        st.warning(output["final_verified_response"])
    else:
        st.error(output["final_verified_response"])

    st.caption(
        "Unsupported and incorrect claims are excluded "
        "from the trusted response."
    )
    st.divider()

    st.write("## 🔎 Claim Verification Results")

    for result_number, result in enumerate(
        output["verification_results"],
        start=1,
    ):
        status = normalize_status(
            result.get("status", "Unsupported")
        )
        confidence_score = safe_confidence_score(
            result.get("confidence_score", 0)
        )
        explanation = result.get(
            "explanation",
            "No explanation was generated.",
        )
        retrieved_evidence = result.get("evidence", [])
        supporting_evidence = (
            get_selected_supporting_evidence(result)
        )

        with st.container(border=True):
            st.write(f"### Claim {result_number}")
            st.write(
                result.get("claim", "Claim unavailable.")
            )

            display_verification_status(
                status=status,
                confidence_score=confidence_score,
            )
            st.progress(confidence_score / 100)

            st.write("#### Explanation")
            st.write(explanation)

            st.write("#### Selected Supporting Evidence")
            st.write(supporting_evidence)

            if retrieved_evidence:
                st.write("#### Retrieved Evidence Sources")

                for evidence_number, evidence in enumerate(
                    retrieved_evidence,
                    start=1,
                ):
                    similarity_score = safe_float(
                        evidence.get("similarity", 0)
                    )
                    source_type = evidence.get(
                        "source_type",
                        "pdf",
                    )
                    source_document = evidence.get(
                        "document",
                        "Unknown source",
                    )
                    source_page = evidence.get(
                        "page",
                        "Unknown",
                    )
                    source_chunk = evidence.get(
                        "chunk_number",
                        "Unknown",
                    )
                    source_url = evidence.get("url", "")
                    source_domain = evidence.get(
                        "domain",
                        "Unknown domain",
                    )
                    relevance_level = evidence.get(
                        "relevance_level",
                        "Unknown relevance",
                    )
                    domain_group = evidence.get(
                        "domain_group",
                        "Not selected",
                    )
                    evidence_text = evidence.get(
                        "text",
                        "Evidence text unavailable.",
                    )

                    if source_type == "web":
                        evidence_title = (
                            f"🌐 Web Evidence {evidence_number} "
                            f"— {source_document} "
                            f"— Relevance: "
                            f"{similarity_score:.4f}"
                        )
                    else:
                        evidence_title = (
                            f"📄 PDF Evidence {evidence_number} "
                            f"— {source_document} "
                            f"— Page {source_page} "
                            f"— Similarity: "
                            f"{similarity_score:.4f}"
                        )

                    with st.expander(evidence_title):
                        if source_type == "web":
                            web_info_column_1, web_info_column_2 = (
                                st.columns(2)
                            )

                            with web_info_column_1:
                                st.write("**Source Type:** WEB")
                                st.write(
                                    f"**Source:** {source_document}"
                                )
                                st.write(
                                    f"**Domain:** {source_domain}"
                                )

                            with web_info_column_2:
                                st.write(
                                    "**Relevance Score:** "
                                    f"{similarity_score:.4f}"
                                )
                                st.write(
                                    "**Relevance Level:** "
                                    f"{relevance_level}"
                                )
                                st.write(
                                    "**Selected Category:** "
                                    f"{domain_group}"
                                )

                            if source_url:
                                st.link_button(
                                    "🔗 Open Web Source",
                                    source_url,
                                )
                        else:
                            pdf_info_column_1, pdf_info_column_2 = (
                                st.columns(2)
                            )

                            with pdf_info_column_1:
                                st.write("**Source Type:** PDF")
                                st.write(
                                    f"**Source:** {source_document}"
                                )

                            with pdf_info_column_2:
                                st.write(
                                    f"**Page:** {source_page}"
                                )
                                st.write(
                                    "**Chunk Number:** "
                                    f"{source_chunk}"
                                )
                                st.write(
                                    "**Similarity Score:** "
                                    f"{similarity_score:.4f}"
                                )

                        st.write("**Evidence Text:**")
                        st.write(evidence_text)
            else:
                st.warning("No related evidence was retrieved.")

    st.divider()

    st.write("## 📥 Download Verification Report")

    pdf_column, json_column, text_column = st.columns(3)

    with pdf_column:
        st.download_button(
            "📕 Download PDF Report",
            data=output["pdf_report"],
            file_name="trustguard_verification_report.pdf",
            mime="application/pdf",
            use_container_width=True,
            on_click="ignore",
        )

    with json_column:
        st.download_button(
            "📄 Download JSON Report",
            data=output["json_report"],
            file_name="trustguard_verification_report.json",
            mime="application/json",
            use_container_width=True,
            on_click="ignore",
        )

    with text_column:
        st.download_button(
            "📝 Download TXT Report",
            data=output["text_report"],
            file_name="trustguard_verification_report.txt",
            mime="text/plain",
            use_container_width=True,
            on_click="ignore",
        )

    st.divider()

    with st.expander("📖 View Extracted PDF Text"):
        st.text_area(
            "PDF Text Preview",
            value=output["pdf_preview"],
            height=450,
            disabled=True,
        )
        st.caption(
            "Only the beginning of the extracted PDF text "
            "is displayed."
        )

    st.info(
        "Trust scores depend on the retrieved PDF and optional "
        "web evidence. A relevance score does not guarantee "
        "factual correctness."
    )


# =========================================================
# LOGIN PROTECTION
# =========================================================

if not st.session_state.logged_in:
    display_authentication_page()
    st.stop()

if not st.session_state.user_id:
    st.error(
        "User session invalid आहे. Logout करून पुन्हा login करा."
    )
    st.stop()


# =========================================================
# APPLICATION HEADER
# =========================================================

st.title("🛡️ TrustGuard AI")
st.subheader("Hallucination Detection & Fact Verification")
st.write(
    "Compare Gemini and Llama answers, select one response "
    "and verify its factual claims using trusted PDFs and "
    "optional web evidence."
)
st.divider()


# =========================================================
# USER INPUT
# =========================================================

question = st.text_area(
    "Enter your question",
    placeholder=(
        "Example: When was the Constitution of India "
        "adopted and when did it come into force?"
    ),
    height=120,
)

uploaded_files = st.file_uploader(
    "Upload trusted PDF documents",
    type=["pdf"],
    accept_multiple_files=True,
)

compare_llms = st.checkbox(
    "🤖 Compare Gemini and Llama answers",
    value=False,
    help=(
        "Generate answers using Gemini and Llama, then "
        "select the response that should be verified."
    ),
)

use_web_verification = st.checkbox(
    "🌐 Use web verification",
    value=False,
    help=(
        "Search trusted web sources in addition to uploaded PDFs."
    ),
)

trusted_domain_group = st.selectbox(
    "Select preferred web-source category",
    options=list(TRUSTED_DOMAIN_GROUPS.keys()),
    index=0,
    disabled=not use_web_verification,
)

minimum_web_score = st.slider(
    "Minimum web relevance score",
    min_value=0.0,
    max_value=1.0,
    value=0.50,
    step=0.05,
    disabled=not use_web_verification,
)


# =========================================================
# GENERATE AND RESET BUTTONS
# =========================================================

generate_column, reset_column = st.columns([3, 1])

with generate_column:
    generate_button = st.button(
        "1️⃣ Generate AI Answer(s)",
        use_container_width=True,
        type="primary",
    )

with reset_column:
    reset_button = st.button(
        "🔄 Reset",
        use_container_width=True,
    )

if reset_button:
    reset_application()
    st.rerun()


# =========================================================
# GENERATE GEMINI AND LLAMA ANSWERS
# =========================================================

if generate_button:
    if not question.strip():
        st.warning("Please enter a factual question.")
    else:
        try:
            st.session_state.verification_output = None

            with st.spinner("Generating Gemini answer..."):
                gemini_answer = generate_ai_answer(question)

            if not gemini_answer or not gemini_answer.strip():
                st.error("Gemini returned an empty answer.")
                st.stop()

            llama_answer = ""

            if compare_llms:
                try:
                    with st.spinner("Generating Llama answer..."):
                        llama_answer = generate_llama_answer(
                            question
                        )
                except Exception as llama_error:
                    st.warning(
                        "Llama answer could not be generated: "
                        f"{llama_error}"
                    )

            st.session_state.gemini_answer = gemini_answer
            st.session_state.llama_answer = llama_answer
            st.session_state.generated_question = question.strip()
            st.session_state.generated_compare_setting = (
                compare_llms
            )
            st.session_state.selected_model = "Gemini"

            st.success("AI answer generation completed.")

        except Exception as error:
            handle_application_error(error)


# =========================================================
# DISPLAY GENERATED ANSWERS
# =========================================================

answers_exist = bool(st.session_state.gemini_answer)
settings_match = (
    st.session_state.generated_question == question.strip()
    and st.session_state.generated_compare_setting == compare_llms
)

if answers_exist and not settings_match:
    st.warning(
        "Question किंवा comparison setting बदलली आहे. "
        "Generate AI Answer(s) button पुन्हा click करा."
    )

if answers_exist and settings_match:
    st.divider()
    st.write("## 🤖 Generated AI Answer(s)")

    available_models = ["Gemini"]

    if st.session_state.llama_answer:
        available_models.append("Llama")

    if len(available_models) == 2:
        gemini_column, llama_column = st.columns(2)

        with gemini_column:
            st.write("### Gemini Answer")
            st.info(st.session_state.gemini_answer)

        with llama_column:
            st.write("### Llama Answer")
            st.info(st.session_state.llama_answer)
    else:
        st.write("### Gemini Answer")
        st.info(st.session_state.gemini_answer)

    if st.session_state.selected_model not in available_models:
        st.session_state.selected_model = available_models[0]

    selected_model = st.radio(
        "Select the answer to verify",
        options=available_models,
        horizontal=True,
        key="selected_model",
    )

    selected_answer = (
        st.session_state.llama_answer
        if selected_model == "Llama"
        else st.session_state.gemini_answer
    )

    st.write(f"**Selected Model:** {selected_model}")

    verify_button = st.button(
        "2️⃣ Verify Selected Answer",
        use_container_width=True,
        type="primary",
    )

    # =====================================================
    # VERIFY SELECTED ANSWER
    # =====================================================

    if verify_button:
        if not uploaded_files:
            st.warning(
                "Please upload at least one trusted PDF."
            )
        elif not selected_answer.strip():
            st.warning("Selected AI answer is empty.")
        else:
            try:
                with st.spinner(
                    "Reading uploaded PDF documents..."
                ):
                    (
                        page_records,
                        total_page_count,
                    ) = extract_multiple_pdfs(uploaded_files)

                if not page_records:
                    st.error(
                        "No readable text was found in the PDFs."
                    )
                    st.stop()

                document_names = [
                    uploaded_file.name
                    for uploaded_file in uploaded_files
                ]
                document_name_text = ", ".join(document_names)

                with st.spinner("Extracting factual claims..."):
                    claims = extract_factual_claims(
                        selected_answer
                    )

                if not claims:
                    st.warning(
                        "No factual claims were found. "
                        "Please ask a more specific question."
                    )
                    st.stop()

                with st.spinner("Creating PDF embeddings..."):
                    chunks, evidence_index = build_evidence_index(
                        page_records
                    )

                if not chunks:
                    st.error(
                        "No searchable PDF chunks were created."
                    )
                    st.stop()

                claim_items = []
                progress_bar = st.progress(0)
                progress_message = st.empty()
                total_claims = len(claims)

                for claim_number, claim in enumerate(
                    claims,
                    start=1,
                ):
                    progress_message.write(
                        f"Finding PDF evidence for claim "
                        f"{claim_number} of {total_claims}..."
                    )

                    pdf_evidence_items = search_evidence(
                        claim=claim,
                        chunks=chunks,
                        index=evidence_index,
                        top_k=5,
                    )

                    for evidence in pdf_evidence_items:
                        evidence["source_type"] = "pdf"
                        evidence["url"] = ""
                        evidence["domain"] = ""
                        evidence["domain_group"] = ""
                        evidence["relevance_level"] = ""

                    combined_evidence = list(pdf_evidence_items)

                    if use_web_verification:
                        progress_message.write(
                            f"Searching web evidence for "
                            f"claim {claim_number}..."
                        )

                        try:
                            web_evidence = search_web_evidence(
                                claim=claim,
                                max_results=5,
                                domain_group=(
                                    trusted_domain_group
                                ),
                                minimum_score=minimum_web_score,
                            )
                            combined_evidence.extend(web_evidence)
                        except Exception as web_error:
                            st.warning(
                                f"Web search failed for claim "
                                f"{claim_number}: {web_error}"
                            )

                    claim_items.append(
                        {
                            "claim": claim,
                            "evidence": combined_evidence,
                        }
                    )

                    progress_bar.progress(
                        claim_number / total_claims
                    )

                progress_message.write(
                    "Verifying all claims in one Gemini request..."
                )

                batch_results = verify_all_claims(claim_items)
                verification_results = []

                for result_index, claim_item in enumerate(
                    claim_items
                ):
                    if result_index < len(batch_results):
                        verification = batch_results[result_index]
                    else:
                        verification = {
                            "status": "Unsupported",
                            "confidence_score": 0,
                            "explanation": (
                                "The verification model did not "
                                "return a result."
                            ),
                            "supporting_evidence": "",
                        }

                    status = normalize_status(
                        verification.get(
                            "status",
                            "Unsupported",
                        )
                    )
                    confidence_score = safe_confidence_score(
                        verification.get(
                            "confidence_score",
                            0,
                        )
                    )

                    verification_results.append(
                        {
                            "claim": claim_item["claim"],
                            "evidence": claim_item["evidence"],
                            "status": status,
                            "confidence_score": confidence_score,
                            "explanation": verification.get(
                                "explanation",
                                "No explanation was generated.",
                            ),
                            "supporting_evidence": (
                                verification.get(
                                    "supporting_evidence",
                                    "",
                                )
                            ),
                        }
                    )

                progress_message.empty()
                progress_bar.empty()

                if not verification_results:
                    st.error(
                        "No verification results were generated."
                    )
                    st.stop()

                overall_score = calculate_overall_score(
                    verification_results
                )
                status_counts = count_statuses(
                    verification_results
                )
                trust_level = get_trust_level(overall_score)
                (
                    pdf_evidence_count,
                    web_evidence_count,
                ) = count_evidence_sources(
                    verification_results
                )
                final_verified_response = build_final_response(
                    verification_results
                )

                report_data = create_report_data(
                    question=question,
                    document_name=document_name_text,
                    ai_answer=selected_answer,
                    overall_score=overall_score,
                    trust_level=trust_level,
                    verification_results=verification_results,
                )

                # User information must be added before reports are created.
                report_data["generated_by"] = (
                    st.session_state.username
                )
                report_data["user_id"] = int(
                    st.session_state.user_id
                )
                report_data["selected_llm"] = selected_model
                report_data["llm_comparison_enabled"] = (
                    compare_llms
                )
                report_data["gemini_answer"] = (
                    st.session_state.gemini_answer
                )
                report_data["llama_answer"] = (
                    st.session_state.llama_answer
                )
                report_data["uploaded_documents"] = (
                    document_names
                )
                report_data["web_verification_enabled"] = (
                    use_web_verification
                )
                report_data["web_domain_group"] = (
                    trusted_domain_group
                )
                report_data[
                    "minimum_web_relevance_score"
                ] = minimum_web_score
                report_data["pdf_evidence_count"] = (
                    pdf_evidence_count
                )
                report_data["web_evidence_count"] = (
                    web_evidence_count
                )

                json_report = create_json_report(report_data)
                text_report = create_text_report(report_data)
                pdf_report = create_pdf_report(report_data)

                saved_record_id = save_verification(
                    report_data=report_data,
                    user_id=int(st.session_state.user_id),
                )

                pdf_preview = create_pdf_preview(
                    page_records,
                    limit=7000,
                )

                st.session_state.verification_output = {
                    "saved_record_id": saved_record_id,
                    "question": question,
                    "selected_model": selected_model,
                    "ai_answer": selected_answer,
                    "comparison_enabled": compare_llms,
                    "gemini_answer": (
                        st.session_state.gemini_answer
                    ),
                    "llama_answer": (
                        st.session_state.llama_answer
                    ),
                    "document_names": document_names,
                    "total_page_count": total_page_count,
                    "chunk_count": len(chunks),
                    "use_web_verification": (
                        use_web_verification
                    ),
                    "trusted_domain_group": (
                        trusted_domain_group
                    ),
                    "minimum_web_score": minimum_web_score,
                    "pdf_evidence_count": pdf_evidence_count,
                    "web_evidence_count": web_evidence_count,
                    "overall_score": overall_score,
                    "status_counts": status_counts,
                    "trust_level": trust_level,
                    "final_verified_response": (
                        final_verified_response
                    ),
                    "verification_results": (
                        verification_results
                    ),
                    "pdf_report": pdf_report,
                    "json_report": json_report,
                    "text_report": text_report,
                    "pdf_preview": pdf_preview,
                }

                st.rerun()

            except Exception as error:
                handle_application_error(error)


# =========================================================
# DISPLAY SAVED VERIFICATION RESULT
# =========================================================

if st.session_state.verification_output:
    st.divider()
    display_verification_output(
        st.session_state.verification_output
    )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.success(
        f"Logged in as: {st.session_state.username}"
    )

    if st.button(
        "🚪 Logout",
        use_container_width=True,
    ):
        logout_user()
        st.rerun()

    st.divider()
    st.title("🛡️ TrustGuard AI")
    st.write("AI-generated answer verification system.")

    st.divider()
    st.write("### Verification Status")
    st.write("✅ Verified")
    st.write("⚠️ Partially Verified")
    st.write("❔ Unsupported")
    st.write("❌ Incorrect")

    st.divider()
    st.write("### System Flow")
    st.write(
        """
        1. Login or register  
        2. Enter a factual question  
        3. Generate Gemini answer  
        4. Generate optional Llama answer  
        5. Select an answer  
        6. Upload trusted PDFs  
        7. Retrieve PDF and web evidence  
        8. Verify all claims  
        9. Calculate trust score  
        10. Save user-specific history
        """
    )

    st.divider()
    st.write("### Current Features")
    st.write("🔐 Login and Registration")
    st.write("👤 User-Specific History")
    st.write("🤖 Gemini vs Llama Comparison")
    st.write("📚 Multiple PDF Upload")
    st.write("🔎 Semantic Evidence Search")
    st.write("📄 PDF and Page Citations")
    st.write("🌐 Optional Web Verification")
    st.write("🏛️ Trusted Domain Filtering")
    st.write("📕 Professional PDF Report")
    st.write("📄 JSON Report")
    st.write("📝 TXT Report")

    st.divider()
    st.caption("TrustGuard AI – Final Year Project")
