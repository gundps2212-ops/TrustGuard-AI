from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
import inspect

import streamlit as st

# =========================================================
# AUTHENTICATION
# =========================================================
from modules.auth_manager import (
    authenticate_user,
    logout_user,
    register_user,
)

# =========================================================
# TRUSTGUARD MODULES
# =========================================================
from modules.claim_extractor import extract_factual_claims
from modules.database_manager import init_database, save_verification
from modules.evidence_retriever import (
    build_evidence_index,
    search_evidence,
)
from modules.llm import generate_ai_answer
from modules.llm_comparison import generate_llama_answer
from modules.nli_detector import (
    analyze_evidence_nli,
    create_nli_summary,
)
from modules.pdf_reader import extract_multiple_pdfs
from modules.pdf_report_generator import create_pdf_report
from modules.report_generator import (
    build_final_response,
    create_json_report,
    create_report_data,
    create_text_report,
)
from modules.reranker import rerank_evidence
from modules.score import (
    calculate_overall_score,
    count_statuses,
    get_trust_level,
)
from modules.trust_score_v2 import calculate_trust_score_v2
from modules.verifier import verify_all_claims
from modules.web_retriever import (
    TRUSTED_DOMAIN_GROUPS,
    search_web_evidence,
)

# =========================================================
# OPTIONAL SOURCE RELIABILITY MODULE
# =========================================================
# If source_reliability.py exists, the project will use it.
# If it does not exist yet, these fallback functions keep
# app.py running instead of producing an import error.
try:
    from modules.source_reliability import (
        analyze_source,
        calculate_average_source_reliability,
        get_source_badge,
    )
    SOURCE_RELIABILITY_AVAILABLE = True
except ImportError:
    SOURCE_RELIABILITY_AVAILABLE = False

    TRUSTED_DOMAINS = {
        "nasa.gov": 98,
        "isro.gov.in": 98,
        "who.int": 95,
        "nih.gov": 96,
        "pubmed.ncbi.nlm.nih.gov": 96,
        "rbi.org.in": 96,
        "gov.in": 95,
        "nic.in": 95,
        "un.org": 94,
        "nature.com": 94,
        "ieee.org": 95,
        "springer.com": 92,
        "sciencedirect.com": 92,
        "worldbank.org": 93,
        "imf.org": 93,
        "wikipedia.org": 75,
    }

    def _normalize_domain(url: str) -> str:
        if not url:
            return ""
        try:
            parsed = urlparse(str(url))
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def _fallback_source_score(url: str) -> float:
        domain = _normalize_domain(url)

        if not domain:
            return 50.0

        for trusted_domain, score in TRUSTED_DOMAINS.items():
            if domain == trusted_domain:
                return float(score)
            if domain.endswith("." + trusted_domain):
                return float(score)

        if domain.endswith(".gov") or domain.endswith(".gov.in"):
            return 95.0

        if domain.endswith(".edu") or domain.endswith(".edu.in"):
            return 90.0

        if domain.endswith(".ac.in"):
            return 90.0

        return 50.0

    def analyze_source(url: str) -> dict[str, Any]:
        score = _fallback_source_score(url)

        if score >= 90:
            category = "Highly Trusted"
        elif score >= 75:
            category = "Trusted"
        elif score >= 60:
            category = "Moderate"
        else:
            category = "Low Confidence"

        return {
            "url": url,
            "domain": _normalize_domain(url),
            "reliability_score": score,
            "category": category,
        }

    def calculate_average_source_reliability(
        urls: list[str],
    ) -> float:
        if not urls:
            return 50.0
        scores = [
            _fallback_source_score(url)
            for url in urls
        ]
        return sum(scores) / len(scores)

    def get_source_badge(score: float) -> str:
        if score >= 90:
            return "🟢 Highly Trusted"
        if score >= 75:
            return "🔵 Trusted"
        if score >= 60:
            return "🟡 Moderate"
        return "🔴 Low Confidence"


# =========================================================
# STREAMLIT PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="TrustGuard AI",
    page_icon="🛡️",
    layout="wide",
)

# =========================================================
# DATABASE INITIALIZATION
# =========================================================
try:
    init_database()
except Exception as error:
    st.warning(f"Database initialization warning: {error}")


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
# SESSION DEFAULTS
# =========================================================
SESSION_DEFAULTS = {
    "logged_in": False,
    "user_id": None,
    "username": "",
    "user_email": "",
    "user_role": "user",
    "access_token": "",
    "refresh_token": "",
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
# BASIC HELPERS
# =========================================================
def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_confidence_score(value: Any) -> float:
    score = safe_float(value, 0.0)
    return max(0.0, min(score, 100.0))


def normalize_status(status: Any) -> str:
    clean_status = str(status or "").strip()

    if clean_status in VALID_STATUSES:
        return clean_status

    return "Unsupported"


# =========================================================
# JSON SAFE CONVERSION
# =========================================================
def make_json_safe(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return [
            make_json_safe(item)
            for item in value
        ]

    if hasattr(value, "item"):
        try:
            return make_json_safe(
                value.item()
            )
        except Exception:
            pass

    if hasattr(value, "model_dump"):
        try:
            return make_json_safe(
                value.model_dump()
            )
        except Exception:
            pass

    if hasattr(value, "dict"):
        try:
            return make_json_safe(
                value.dict()
            )
        except Exception:
            pass

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


# =========================================================
# NORMALIZE VERIFIER OUTPUT
# =========================================================
def normalize_verification_results(
    results: Any,
) -> list[dict[str, Any]]:
    if results is None:
        return []

    if hasattr(results, "results"):
        results = results.results

    if hasattr(results, "verifications"):
        results = results.verifications

    if not isinstance(results, list):
        results = [results]

    normalized_results = []

    for result in results:
        if isinstance(result, dict):
            row = result

        elif hasattr(result, "model_dump"):
            row = result.model_dump()

        elif hasattr(result, "dict"):
            row = result.dict()

        else:
            continue

        row = make_json_safe(row)

        row["status"] = normalize_status(
            row.get("status")
        )

        row["confidence_score"] = (
            safe_confidence_score(
                row.get(
                    "confidence_score",
                    0,
                )
            )
        )

        normalized_results.append(row)

    return normalized_results


# =========================================================
# CLAIM TEXT HELPER
# =========================================================
def get_claim_text(claim: Any) -> str:
    if isinstance(claim, dict):
        return str(
            claim.get(
                "claim",
                claim.get(
                    "text",
                    "",
                ),
            )
        ).strip()

    return str(claim or "").strip()


# =========================================================
# DISPLAY STATUS
# =========================================================
def display_verification_status(
    status: str,
) -> None:
    status = normalize_status(status)

    if status == "Verified":
        st.success("✅ Verified")

    elif status == "Partially Verified":
        st.warning("⚠️ Partially Verified")

    elif status == "Incorrect":
        st.error("❌ Incorrect")

    else:
        st.info("❔ Unsupported")


# =========================================================
# SUPPORTING EVIDENCE
# =========================================================
def get_selected_supporting_evidence(
    result: dict[str, Any],
) -> str:
    value = result.get(
        "supporting_evidence",
        "",
    )

    if isinstance(value, list):
        return "\n\n".join(
            str(item)
            for item in value
        )

    return str(value or "")


# =========================================================
# SOURCE URL HELPERS
# =========================================================
def get_evidence_url(
    evidence: dict[str, Any],
) -> str:
    return str(
        evidence.get(
            "url",
            evidence.get(
                "source_url",
                "",
            ),
        )
        or ""
    ).strip()


def apply_source_reliability(
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """
    Add source reliability metadata to one evidence item.
    PDF evidence without a URL is kept at a neutral 50 score.
    """
    if not isinstance(evidence, dict):
        return evidence

    url = get_evidence_url(evidence)

    if url:
        try:
            analysis = analyze_source(url)

            evidence["source_reliability"] = (
                safe_float(
                    analysis.get(
                        "reliability_score",
                        50,
                    ),
                    50,
                )
            )

            evidence["source_category"] = (
                analysis.get(
                    "category",
                    "Moderate",
                )
            )

            if not evidence.get("domain"):
                evidence["domain"] = (
                    analysis.get(
                        "domain",
                        "",
                    )
                )

        except Exception:
            evidence["source_reliability"] = 50.0
            evidence["source_category"] = "Moderate"

    else:
        evidence.setdefault(
            "source_reliability",
            50.0,
        )
        evidence.setdefault(
            "source_category",
            "Document Source",
        )

    return evidence


def enrich_sources(
    verification_results: list[dict[str, Any]],
) -> list[str]:
    """
    Add source reliability to every evidence item
    and return unique web URLs.
    """
    urls = []

    for result in verification_results:
        evidence_list = result.get(
            "evidence",
            [],
        )

        if not isinstance(
            evidence_list,
            list,
        ):
            continue

        for evidence in evidence_list:
            if not isinstance(
                evidence,
                dict,
            ):
                continue

            apply_source_reliability(
                evidence
            )

            url = get_evidence_url(
                evidence
            )

            if url:
                urls.append(url)

    return list(
        dict.fromkeys(urls)
    )


# =========================================================
# EVIDENCE AGREEMENT
# =========================================================
def calculate_evidence_agreement(
    verification_results: list[dict[str, Any]],
) -> float:
    """
    Estimate agreement from verifier status + NLI evidence.
    This is intentionally deterministic and transparent.
    """

    if not verification_results:
        return 0.0

    claim_scores = []

    for result in verification_results:
        status = normalize_status(
            result.get("status")
        )

        evidence_list = result.get(
            "evidence",
            [],
        )

        if not isinstance(
            evidence_list,
            list,
        ):
            evidence_list = []

        if not evidence_list:
            claim_scores.append(
                50.0
            )
            continue

        entailments = []
        contradictions = []

        for evidence in evidence_list:
            if not isinstance(
                evidence,
                dict,
            ):
                continue

            entailments.append(
                safe_float(
                    evidence.get(
                        "entailment_score",
                        0,
                    )
                )
            )

            contradictions.append(
                safe_float(
                    evidence.get(
                        "contradiction_score",
                        0,
                    )
                )

            )

        if entailments:
            support = (
                sum(entailments)
                / len(entailments)
            )

            contradiction = (
                sum(contradictions)
                / len(contradictions)
            )

            score = (
                50
                + (
                    support
                    - contradiction
                )
                * 50
            )

        else:
            if status == "Verified":
                score = 90.0
            elif status == "Partially Verified":
                score = 70.0
            elif status == "Incorrect":
                score = 20.0
            else:
                score = 50.0

        claim_scores.append(
            max(
                0.0,
                min(
                    score,
                    100.0,
                ),
            )
        )

    if not claim_scores:
        return 50.0

    return sum(claim_scores) / len(
        claim_scores
    )


# =========================================================
# SAFE TRUST SCORE V2
# =========================================================
def calculate_trust_metrics_safe(
    verification_results: list[dict[str, Any]],
) -> dict[str, float]:
    """
    Prefer modules.trust_score_v2.
    If that module raises an error because one of the
    advanced fields is missing, use a transparent fallback.
    """

    try:
        metrics = calculate_trust_score_v2(
            verification_results
        )

        if isinstance(metrics, dict):
            return {
                "verifier": safe_float(
                    metrics.get(
                        "verifier",
                        0,
                    )
                ),
                "reranker": safe_float(
                    metrics.get(
                        "reranker",
                        0,
                    )
                ),
                "nli": safe_float(
                    metrics.get(
                        "nli",
                        0,
                    )
                ),
                "source": safe_float(
                    metrics.get(
                        "source",
                        0,
                    )
                ),
                "agreement": safe_float(
                    metrics.get(
                        "agreement",
                        0,
                    )
                ),
                "final_score": safe_float(
                    metrics.get(
                        "final_score",
                        0,
                    )
                ),
            }

    except Exception:
        pass

    # -----------------------------------------------------
    # Transparent fallback
    # -----------------------------------------------------
    if not verification_results:
        return {
            "verifier": 0.0,
            "reranker": 0.0,
            "nli": 0.0,
            "source": 0.0,
            "agreement": 0.0,
            "final_score": 0.0,
        }

    verifier_scores = []
    reranker_scores = []
    nli_scores = []
    source_scores = []

    for result in verification_results:
        verifier_scores.append(
            safe_confidence_score(
                result.get(
                    "confidence_score",
                    0,
                )
            )
        )

        evidence_list = result.get(
            "evidence",
            [],
        )

        if not isinstance(
            evidence_list,
            list,
        ):
            evidence_list = []

        if evidence_list:
            reranker_values = []
            nli_values = []
            source_values = []

            for evidence in evidence_list:
                if not isinstance(
                    evidence,
                    dict,
                ):
                    continue

                reranker = safe_float(
                    evidence.get(
                        "reranker_score",
                        evidence.get(
                            "cross_encoder_score",
                            0,
                        ),
                    )
                )

                # Convert common CrossEncoder logit/range
                # into a safe 0-100 display score.
                if reranker <= 1:
                    reranker *= 100

                reranker_values.append(
                    max(
                        0.0,
                        min(
                            reranker,
                            100.0,
                        ),
                    )
                )

                entailment = safe_float(
                    evidence.get(
                        "entailment_score",
                        0,
                    )
                )

                contradiction = safe_float(
                    evidence.get(
                        "contradiction_score",
                        0,
                    )
                )

                nli_value = (
                    entailment
                    / max(
                        entailment
                        + contradiction,
                        1e-9,
                    )
                    * 100
                )

                nli_values.append(
                    max(
                        0.0,
                        min(
                            nli_value,
                            100.0,
                        ),
                    )
                )

                source_values.append(
                    safe_float(
                        evidence.get(
                            "source_reliability",
                            50,
                        ),
                        50,
                    )
                )

            reranker_scores.append(
                sum(reranker_values)
                / len(reranker_values)
                if reranker_values
                else 50.0
            )

            nli_scores.append(
                sum(nli_values)
                / len(nli_values)
                if nli_values
                else 50.0
            )

            source_scores.append(
                sum(source_values)
                / len(source_values)
                if source_values
                else 50.0
            )

        else:
            reranker_scores.append(50.0)
            nli_scores.append(50.0)
            source_scores.append(50.0)

    verifier = (
        sum(verifier_scores)
        / len(verifier_scores)
    )

    reranker = (
        sum(reranker_scores)
        / len(reranker_scores)
    )

    nli = (
        sum(nli_scores)
        / len(nli_scores)
    )

    source = (
        sum(source_scores)
        / len(source_scores)
    )

    agreement = (
        calculate_evidence_agreement(
            verification_results
        )
    )

    final_score = (
        verifier * 0.35
        + reranker * 0.25
        + nli * 0.20
        + source * 0.10
        + agreement * 0.10
    )

    return {
        "verifier": round(
            verifier,
            2,
        ),
        "reranker": round(
            reranker,
            2,
        ),
        "nli": round(
            nli,
            2,
        ),
        "source": round(
            source,
            2,
        ),
        "agreement": round(
            agreement,
            2,
        ),
        "final_score": round(
            max(
                0.0,
                min(
                    final_score,
                    100.0,
                ),
            ),
            2,
        ),
    }


# =========================================================
# NLI ADAPTER
# =========================================================
def run_nli_pipeline(
    verification_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Supports the current two-argument NLI implementation and
    also remains compatible with a one-argument bulk implementation.
    """

    if not verification_results:
        return {
            "results": verification_results,
            "summary": {
                "overall_relation": "neutral",
                "strongest_entailment": 0.0,
                "strongest_contradiction": 0.0,
                "strongest_neutral": 0.0,
                "entailment_count": 0,
                "contradiction_count": 0,
                "neutral_count": 0,
            },
        }

    try:
        signature = inspect.signature(
            analyze_evidence_nli
        )

        parameters = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind
            in (
                parameter.POSITIONAL_ONLY,
                parameter.POSITIONAL_OR_KEYWORD,
            )
        ]

    except Exception:
        parameters = []

    # -----------------------------------------------------
    # Current implementation:
    # analyze_evidence_nli(claim, evidence_items)
    # -----------------------------------------------------
    if len(parameters) >= 2:
        all_evidence = []

        for result in verification_results:
            claim = str(
                result.get(
                    "claim",
                    "",
                )
            )

            evidence_list = result.get(
                "evidence",
                [],
            )

            if not isinstance(
                evidence_list,
                list,
            ):
                evidence_list = []

            if not evidence_list:
                continue

            try:
                enriched = (
                    analyze_evidence_nli(
                        claim=claim,
                        evidence_items=evidence_list,
                    )
                )

                if isinstance(
                    enriched,
                    list,
                ):
                    result["evidence"] = (
                        enriched
                    )

            except Exception as error:
                result["nli_error"] = str(
                    error
                )

            for evidence in result.get(
                "evidence",
                [],
            ):
                if isinstance(
                    evidence,
                    dict,
                ):
                    all_evidence.append(
                        evidence
                    )

        try:
            summary = create_nli_summary(
                all_evidence
            )
        except Exception:
            summary = {
                "overall_relation": "neutral",
                "strongest_entailment": 0.0,
                "strongest_contradiction": 0.0,
                "strongest_neutral": 0.0,
                "entailment_count": 0,
                "contradiction_count": 0,
                "neutral_count": 0,
            }

        return {
            "results": verification_results,
            "summary": summary,
        }

    # -----------------------------------------------------
    # One-argument bulk implementation
    # -----------------------------------------------------
    try:
        bulk_results = analyze_evidence_nli(
            verification_results
        )

        if isinstance(
            bulk_results,
            list,
        ):
            verification_results = (
                normalize_verification_results(
                    bulk_results
                )
            )

    except Exception:
        pass

    try:
        summary = create_nli_summary(
            verification_results
        )
    except Exception:
        summary = {
            "overall_relation": "neutral",
            "strongest_entailment": 0.0,
            "strongest_contradiction": 0.0,
            "strongest_neutral": 0.0,
            "entailment_count": 0,
            "contradiction_count": 0,
            "neutral_count": 0,
        }

    return {
        "results": verification_results,
        "summary": summary,
    }


# =========================================================
# DISPLAY EVIDENCE
# =========================================================
def display_evidence_item(
    evidence: dict[str, Any],
    evidence_number: int,
) -> None:
    source_type = str(
        evidence.get(
            "source_type",
            "pdf",
        )
    ).lower()

    source_name = str(
        evidence.get(
            "source_name",
            evidence.get(
                "document",
                "Unknown Source",
            ),
        )
    )

    evidence_text = str(
        evidence.get(
            "text",
            evidence.get(
                "content",
                evidence.get(
                    "snippet",
                    "",
                ),
            ),
        )
    )

    # =====================================================
    # WEB EVIDENCE
    # =====================================================
    if source_type == "web":
        st.markdown(
            f"**{evidence_number}. 🌐 "
            f"{source_name}**"
        )

        domain = evidence.get(
            "domain"
        )

        if domain:
            st.caption(
                f"Domain: {domain}"
            )

        web_score = safe_float(
            evidence.get(
                "relevance_score",
                evidence.get(
                    "score",
                    0,
                ),
            )
        )

        if web_score > 0:
            st.caption(
                f"Web Relevance: "
                f"{web_score:.3f}"
            )

        source_reliability = safe_float(
            evidence.get(
                "source_reliability",
                50,
            ),
            50,
        )

        st.caption(
            f"🌐 Source Reliability: "
            f"{source_reliability:.1f}/100 "
            f"— "
            f"{get_source_badge(source_reliability)}"
        )

        url = evidence.get(
            "url"
        )

        if url:
            st.markdown(
                f"[Open Web Source]({url})"
            )

        # NLI information
        nli_label = evidence.get(
            "nli_label"
        )

        if nli_label:
            if nli_label == "entailment":
                st.success(
                    "🟢 NLI: Evidence Supports Claim"
                )
            elif nli_label == "contradiction":
                st.error(
                    "🔴 NLI: Evidence Contradicts Claim"
                )
            else:
                st.info(
                    "⚪ NLI: Neutral Evidence"
                )

            st.caption(
                f"Entailment: "
                f"{safe_float(evidence.get('entailment_score', 0)):.3f} | "
                f"Contradiction: "
                f"{safe_float(evidence.get('contradiction_score', 0)):.3f} | "
                f"Neutral: "
                f"{safe_float(evidence.get('neutral_score', 0)):.3f}"
            )

        if evidence_text:
            st.write(
                evidence_text
            )

        return

    # =====================================================
    # PDF INFORMATION
    # =====================================================
    page_number = evidence.get(
        "page",
        "Unknown",
    )

    chunk_number = evidence.get(
        "chunk_number"
    )

    st.markdown(
        f"**{evidence_number}. 📄 "
        f"{source_name} — Page "
        f"{page_number}**"
    )

    if chunk_number:
        st.caption(
            f"Chunk: {chunk_number}"
        )

    # =====================================================
    # HYBRID SCORES
    # =====================================================
    semantic_score = safe_float(
        evidence.get(
            "semantic_score",
            0,
        )
    )

    bm25_score = safe_float(
        evidence.get(
            "bm25_score",
            0,
        )
    )

    hybrid_score = safe_float(
        evidence.get(
            "hybrid_score",
            evidence.get(
                "similarity",
                0,
            ),
        )
    )

    st.caption(
        f"🔎 Semantic: "
        f"{semantic_score:.3f} | "
        f"BM25: "
        f"{bm25_score:.3f} | "
        f"Hybrid: "
        f"{hybrid_score:.3f}"
    )

    # =====================================================
    # CROSS-ENCODER SCORE
    # =====================================================
    if "reranker_score" in evidence:
        reranker_score = safe_float(
            evidence.get(
                "reranker_score",
                0,
            )
        )

        st.caption(
            f"🧠 Cross-Encoder Score: "
            f"{reranker_score:.3f}"
        )

    # =====================================================
    # SOURCE RELIABILITY
    # =====================================================
    source_reliability = safe_float(
        evidence.get(
            "source_reliability",
            50,
        ),
        50,
    )

    st.caption(
        f"🏷️ Source Reliability: "
        f"{source_reliability:.1f}/100"
    )

    # =====================================================
    # NLI
    # =====================================================
    nli_label = evidence.get(
        "nli_label"
    )

    if nli_label:
        if nli_label == "entailment":
            st.success(
                "🟢 NLI: Evidence Supports Claim"
            )
        elif nli_label == "contradiction":
            st.error(
                "🔴 NLI: Evidence Contradicts Claim"
            )
        else:
            st.info(
                "⚪ NLI: Neutral Evidence"
            )

        st.caption(
            f"Entailment: "
            f"{safe_float(evidence.get('entailment_score', 0)):.3f} | "
            f"Contradiction: "
            f"{safe_float(evidence.get('contradiction_score', 0)):.3f} | "
            f"Neutral: "
            f"{safe_float(evidence.get('neutral_score', 0)):.3f}"
        )

    # =====================================================
    # RANK CHANGES
    # =====================================================
    pre_rerank_rank = evidence.get(
        "pre_rerank_rank",
        evidence.get(
            "retrieval_rank"
        ),
    )

    final_rank = evidence.get(
        "final_rank"
    )

    if (
        pre_rerank_rank
        and final_rank
    ):
        st.caption(
            f"📊 Hybrid Rank: "
            f"{pre_rerank_rank} → "
            f"Final Rank: "
            f"{final_rank}"
        )

    elif evidence.get(
        "retrieval_rank"
    ):
        st.caption(
            f"Hybrid Rank: "
            f"{evidence.get('retrieval_rank')}"
        )

    pipeline = evidence.get(
        "retrieval_pipeline"
    )

    if pipeline:
        st.caption(
            f"Pipeline: {pipeline}"
        )

    if evidence_text:
        st.write(
            evidence_text
        )


# =========================================================
# COUNT EVIDENCE SOURCES
# =========================================================
def count_evidence_sources(
    verification_results: list[
        dict[str, Any]
    ],
) -> tuple[int, int]:

    pdf_count = 0
    web_count = 0

    for result in verification_results:
        evidence_list = result.get(
            "evidence",
            [],
        )

        if not isinstance(
            evidence_list,
            list,
        ):
            continue

        for evidence in evidence_list:
            if not isinstance(
                evidence,
                dict,
            ):
                continue

            source_type = str(
                evidence.get(
                    "source_type",
                    "pdf",
                )
            ).lower()

            if source_type == "web":
                web_count += 1
            else:
                pdf_count += 1

    return (
        pdf_count,
        web_count,
    )


# =========================================================
# RESET VERIFICATION
# =========================================================
def reset_verification_state() -> None:
    st.session_state[
        "verification_output"
    ] = None


# =========================================================
# CLEAR LOGIN SESSION
# =========================================================
def clear_login_session() -> None:
    for key, default_value in SESSION_DEFAULTS.items():
        st.session_state[key] = default_value


# =========================================================
# AUTHENTICATION PAGE
# =========================================================
def display_authentication_page() -> None:
    st.title(
        "🛡️ TrustGuard AI"
    )

    st.subheader(
        "Hallucination Detection & Fact Verification"
    )

    st.write(
        "Login or create your TrustGuard AI account."
    )

    login_tab, register_tab = st.tabs(
        [
            "🔐 Login",
            "📝 Register",
        ]
    )

    # =====================================================
    # LOGIN
    # =====================================================
    with login_tab:
        with st.form(
            "login_form"
        ):
            login_email = st.text_input(
                "Email",
                placeholder="example@gmail.com",
            )

            login_password = st.text_input(
                "Password",
                type="password",
            )

            login_button = st.form_submit_button(
                "Login",
                type="primary",
                use_container_width=True,
            )

        if login_button:
            if not login_email.strip() or not login_password:
                st.error(
                    "Please enter email and password."
                )
            else:
                try:
                    with st.spinner(
                        "Logging in..."
                    ):
                        user = authenticate_user(
                            email=login_email.strip(),
                            password=login_password,
                        )

                    if user is None:
                        st.error(
                            "Login failed. "
                            "Please check your email and password."
                        )
                    else:
                        st.session_state[
                            "logged_in"
                        ] = True

                        # Supabase UUID must remain a string.
                        st.session_state[
                            "user_id"
                        ] = user.get(
                            "id"
                        )

                        st.session_state[
                            "username"
                        ] = user.get(
                            "username",
                            "User",
                        )

                        st.session_state[
                            "user_email"
                        ] = user.get(
                            "email",
                            login_email,
                        )

                        st.session_state[
                            "user_role"
                        ] = user.get(
                            "role",
                            "user",
                        )

                        st.session_state[
                            "access_token"
                        ] = user.get(
                            "access_token",
                            "",
                        )

                        st.session_state[
                            "refresh_token"
                        ] = user.get(
                            "refresh_token",
                            "",
                        )

                        st.success(
                            "Login successful."
                        )

                        st.rerun()

                except Exception as error:
                    st.error(
                        "Login error."
                    )
                    st.code(
                        str(error)
                    )

    # =====================================================
    # REGISTER
    # =====================================================
    with register_tab:
        with st.form(
            "register_form"
        ):
            register_username = st.text_input(
                "Username"
            )

            register_email = st.text_input(
                "Email",
                key="register_email",
            )

            register_password = st.text_input(
                "Password",
                type="password",
                key="register_password",
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
            )

            register_button = st.form_submit_button(
                "Create Account",
                type="primary",
                use_container_width=True,
            )

        if register_button:
            try:
                success, message = register_user(
                    username=register_username,
                    email=register_email,
                    password=register_password,
                    confirm_password=confirm_password,
                )

                if success:
                    st.success(
                        message
                    )
                else:
                    st.error(
                        message
                    )

            except Exception as error:
                st.error(
                    "Registration error."
                )
                st.code(
                    str(error)
                )


# =========================================================
# LOGIN REQUIRED
# =========================================================
if not st.session_state.get(
    "logged_in",
    False,
):
    display_authentication_page()
    st.stop()


# =========================================================
# SUPABASE SESSION
# =========================================================
user_id = st.session_state.get(
    "user_id"
)

access_token = st.session_state.get(
    "access_token",
    "",
)

refresh_token = st.session_state.get(
    "refresh_token",
    "",
)

if not user_id:
    st.error(
        "Invalid user session. "
        "Please logout and login again."
    )
    st.stop()

if (
    not access_token
    or not refresh_token
):
    st.error(
        "Supabase session is missing. "
        "Please logout and login again."
    )
    st.stop()


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.title(
        "🛡️ TrustGuard AI"
    )

    sidebar_output = st.session_state.get(
        "verification_output"
    )

    if (
        sidebar_output
        and sidebar_output.get(
            "trust_metrics"
        )
    ):
        st.metric(
            "Trust Score V2",
            f"{safe_float(sidebar_output['trust_metrics'].get('final_score', 0)):.1f}%",
        )
    else:
        st.caption(
            "Trust Score V2: not yet calculated"
        )

    st.write(
        f"👤 **"
        f"{st.session_state.get('username', 'User')}"
        f"**"
    )

    st.caption(
        st.session_state.get(
            "user_email",
            "",
        )
    )

    current_role = str(
        st.session_state.get(
            "user_role",
            "user",
        )
    ).title()

    st.write(
        f"Role: **{current_role}**"
    )

    with st.expander(
        "Session Information"
    ):
        st.caption(
            "Supabase User UUID"
        )

        st.code(
            str(
                st.session_state.get(
                    "user_id"
                )
            )
        )

    if st.button(
        "🚪 Logout",
        use_container_width=True,
    ):
        try:
            logout_user(
                access_token=access_token,
                refresh_token=refresh_token,
            )
        except Exception:
            pass

        clear_login_session()
        st.rerun()

    st.divider()

    st.write(
        "### Advanced Features"
    )

    st.write(
        """
        📄 Multi-PDF Verification
        🧠 Gemini AI
        🦙 Llama Comparison
        🔎 Semantic Search
        🧮 BM25 Keyword Search
        🔗 FAISS + BM25 Hybrid Retrieval
        🧠 Cross-Encoder Reranking
        ⚖️ NLI Contradiction Detection
        🌐 Trusted Web Verification
        🏷️ Source Reliability
        📊 Trust Score V2
        📑 Verification Reports
        ☁️ Supabase Cloud Storage
        """
    )


# =========================================================
# HEADER
# =========================================================
st.title(
    "🛡️ TrustGuard AI"
)

st.subheader(
    "Hallucination Detection & Fact Verification"
)

st.write(
    "Verify AI-generated factual claims using "
    "trusted PDF documents, Hybrid Retrieval, "
    "Cross-Encoder reranking, NLI and web evidence."
)

st.divider()


# =========================================================
# QUESTION INPUT
# =========================================================
question = st.text_area(
    "❓ Enter your question",
    height=120,
    placeholder=(
        "Example: What are the key findings "
        "described in the uploaded documents?"
    ),
)


# =========================================================
# PDF UPLOAD
# =========================================================
uploaded_files = st.file_uploader(
    "📄 Upload Trusted PDF Documents",
    type=["pdf"],
    accept_multiple_files=True,
)


# =========================================================
# SETTINGS
# =========================================================
st.write(
    "### ⚙️ Verification Settings"
)

settings_col1, settings_col2, settings_col3 = (
    st.columns(3)
)

with settings_col1:
    compare_llms = st.checkbox(
        "Compare Gemini with Llama",
        value=False,
    )

    enable_nli = st.checkbox(
        "Enable Contradiction Detection (NLI)",
        value=True,
        help=(
            "Detect whether evidence supports, "
            "contradicts or is neutral toward a claim."
        ),
    )

    enable_web_verification = st.checkbox(
        "Enable Trusted Web Verification",
        value=False,
    )

with settings_col2:
    if isinstance(
        TRUSTED_DOMAIN_GROUPS,
        dict,
    ):
        domain_options = list(
            TRUSTED_DOMAIN_GROUPS.keys()
        )
    else:
        domain_options = list(
            TRUSTED_DOMAIN_GROUPS
        )

    if not domain_options:
        domain_options = [
            "No domain filter"
        ]

    selected_domain_group = st.selectbox(
        "Trusted Web Domain Group",
        options=domain_options,
        disabled=not enable_web_verification,
    )

    minimum_web_score = st.slider(
        "Minimum Web Relevance",
        min_value=0.0,
        max_value=1.0,
        value=0.50,
        step=0.05,
        disabled=not enable_web_verification,
    )

with settings_col3:
    enable_reranking = st.checkbox(
        "Enable Cross-Encoder Reranking",
        value=True,
        help=(
            "Rerank hybrid search candidates "
            "with a cross-encoder model."
        ),
    )

st.divider()


# =========================================================
# GENERATE ANSWER
# =========================================================
generate_button = st.button(
    "🤖 Generate AI Answer",
    type="primary",
    use_container_width=True,
)

if generate_button:
    reset_verification_state()

    if not question.strip():
        st.error(
            "Please enter a question."
        )
    else:
        try:
            with st.spinner(
                "Generating Gemini answer..."
            ):
                gemini_answer = (
                    generate_ai_answer(
                        question.strip()
                    )
                )

            st.session_state[
                "gemini_answer"
            ] = gemini_answer

            st.session_state[
                "generated_question"
            ] = question.strip()

            st.session_state[
                "generated_compare_setting"
            ] = compare_llms

            if compare_llms:
                try:
                    with st.spinner(
                        "Generating Llama answer..."
                    ):
                        llama_answer = (
                            generate_llama_answer(
                                question.strip()
                            )
                        )

                    st.session_state[
                        "llama_answer"
                    ] = llama_answer

                except Exception as error:
                    st.session_state[
                        "llama_answer"
                    ] = ""

                    st.warning(
                        "Llama comparison failed: "
                        f"{error}"
                    )
            else:
                st.session_state[
                    "llama_answer"
                ] = ""

            st.success(
                "AI answer generated successfully."
            )

        except Exception as error:
            st.error(
                "Unable to generate AI answer."
            )
            st.code(
                str(error)
            )


# =========================================================
# GENERATED ANSWER
# =========================================================
gemini_answer = st.session_state.get(
    "gemini_answer",
    "",
)

llama_answer = st.session_state.get(
    "llama_answer",
    "",
)

if gemini_answer:
    st.write(
        "## 🤖 Generated Answer"
    )

    available_models = [
        "Gemini"
    ]

    if llama_answer:
        available_models.append(
            "Llama"
        )

    selected_model = st.radio(
        "Select answer to verify",
        options=available_models,
        horizontal=True,
    )

    st.session_state[
        "selected_model"
    ] = selected_model

    selected_answer = (
        gemini_answer
        if selected_model == "Gemini"
        else llama_answer
    )

    with st.container(
        border=True
    ):
        st.write(
            f"### {selected_model} Answer"
        )

        st.write(
            selected_answer
        )

    if llama_answer:
        with st.expander(
            "🔄 Compare Gemini and Llama"
        ):
            gemini_col, llama_col = (
                st.columns(2)
            )

            with gemini_col:
                st.write(
                    "### Gemini"
                )
                st.write(
                    gemini_answer
                )

            with llama_col:
                st.write(
                    "### Llama"
                )
                st.write(
                    llama_answer
                )

    st.divider()

    # =====================================================
    # VERIFY BUTTON
    # =====================================================
    verify_button = st.button(
        "🔍 Verify Selected Answer",
        type="primary",
        use_container_width=True,
    )

    if verify_button:

        if (
            not uploaded_files
            and not enable_web_verification
        ):
            st.error(
                "Upload at least one PDF "
                "or enable web verification."
            )

        else:
            try:
                verification_question = (
                    st.session_state.get(
                        "generated_question",
                        question,
                    )
                )

                # =========================================
                # READ PDF
                # =========================================
                page_records = []
                total_pages = 0

                if uploaded_files:
                    with st.spinner(
                        "Reading PDF documents..."
                    ):
                        (
                            page_records,
                            total_pages,
                        ) = extract_multiple_pdfs(
                            uploaded_files
                        )

                # =========================================
                # BUILD HYBRID INDEX
                # =========================================
                evidence_chunks = []
                evidence_index = None

                if page_records:
                    with st.spinner(
                        "Building FAISS + BM25 Hybrid Index..."
                    ):
                        (
                            evidence_chunks,
                            evidence_index,
                        ) = build_evidence_index(
                            page_records
                        )

                # =========================================
                # EXTRACT FACTUAL CLAIMS
                # =========================================
                with st.spinner(
                    "Extracting factual claims..."
                ):
                    raw_claims = (
                        extract_factual_claims(
                            selected_answer
                        )
                    )

                claims = []

                for raw_claim in (
                    raw_claims or []
                ):
                    claim_text = get_claim_text(
                        raw_claim
                    )

                    if claim_text:
                        claims.append(
                            claim_text
                        )

                if not claims:
                    st.warning(
                        "No factual claims were extracted."
                    )
                    st.stop()

                # =========================================
                # RETRIEVE EVIDENCE
                # =========================================
                claim_items = []

                progress_bar = st.progress(
                    0
                )

                progress_text = st.empty()

                total_claims = len(
                    claims
                )

                for claim_index, claim in enumerate(
                    claims,
                    start=1,
                ):
                    progress_text.write(
                        f"Processing claim "
                        f"{claim_index}/"
                        f"{total_claims}..."
                    )

                    combined_evidence = []

                    # =====================================
                    # STAGE 1:
                    # FAISS + BM25 HYBRID SEARCH
                    # =====================================
                    if (
                        evidence_chunks
                        and evidence_index
                        is not None
                    ):
                        hybrid_candidates = (
                            search_evidence(
                                query=claim,
                                chunks=evidence_chunks,
                                index=evidence_index,
                                top_k=10,
                            )
                        )

                        # =================================
                        # STAGE 2:
                        # CROSS-ENCODER RERANKING
                        # =================================
                        if (
                            enable_reranking
                            and hybrid_candidates
                        ):
                            try:
                                with st.spinner(
                                    "Cross-Encoder "
                                    f"reranking claim "
                                    f"{claim_index}..."
                                ):
                                    pdf_evidence = (
                                        rerank_evidence(
                                            query=claim,
                                            evidence_items=(
                                                hybrid_candidates
                                            ),
                                            top_k=5,
                                        )
                                    )

                            except Exception as error:
                                st.warning(
                                    "Cross-Encoder reranking "
                                    "failed for one claim. "
                                    "Using Hybrid Search results. "
                                    f"{error}"
                                )

                                pdf_evidence = (
                                    hybrid_candidates[:5]
                                )

                        else:
                            pdf_evidence = (
                                hybrid_candidates[:5]
                            )

                        # =================================
                        # SOURCE METADATA
                        # =================================
                        for evidence in pdf_evidence:
                            evidence[
                                "source_type"
                            ] = "pdf"

                            if not evidence.get(
                                "source_name"
                            ):
                                evidence[
                                    "source_name"
                                ] = evidence.get(
                                    "document",
                                    "PDF Document",
                                )

                            apply_source_reliability(
                                evidence
                            )

                        combined_evidence.extend(
                            pdf_evidence
                        )

                    # =====================================
                    # WEB VERIFICATION
                    # =====================================
                    if enable_web_verification:
                        try:
                            web_evidence = (
                                search_web_evidence(
                                    claim,
                                    max_results=5,
                                    domain_group=(
                                        selected_domain_group
                                    ),
                                    minimum_score=(
                                        minimum_web_score
                                    ),
                                )
                            )

                            for evidence in (
                                web_evidence or []
                            ):
                                evidence[
                                    "source_type"
                                ] = "web"

                                if not evidence.get(
                                    "source_name"
                                ):
                                    evidence[
                                        "source_name"
                                    ] = (
                                        evidence.get(
                                            "title"
                                        )
                                        or evidence.get(
                                            "domain"
                                        )
                                        or evidence.get(
                                            "url"
                                        )
                                        or "Web Source"
                                    )

                                apply_source_reliability(
                                    evidence
                                )

                            combined_evidence.extend(
                                web_evidence or []
                            )

                        except Exception as error:
                            st.warning(
                                "Web retrieval failed "
                                "for one claim: "
                                f"{error}"
                            )

                    # =====================================
                    # CLAIM + EVIDENCE
                    # =====================================
                    claim_items.append(
                        {
                            "claim": claim,
                            "evidence": combined_evidence,
                        }
                    )

                    progress_bar.progress(
                        claim_index
                        / total_claims
                    )

                progress_text.empty()

                # =========================================
                # VERIFY CLAIMS
                # =========================================
                with st.spinner(
                    "Verifying factual claims..."
                ):
                    raw_results = (
                        verify_all_claims(
                            claim_items
                        )
                    )

                verification_results = (
                    normalize_verification_results(
                        raw_results
                    )
                )

                # =========================================
                # ATTACH EVIDENCE
                # =========================================
                for index, result in enumerate(
                    verification_results
                ):
                    if (
                        index
                        >= len(
                            claim_items
                        )
                    ):
                        continue

                    if not result.get(
                        "claim"
                    ):
                        result[
                            "claim"
                        ] = claim_items[
                            index
                        ][
                            "claim"
                        ]

                    if not result.get(
                        "evidence"
                    ):
                        result[
                            "evidence"
                        ] = claim_items[
                            index
                        ][
                            "evidence"
                        ]

                    # Add source reliability even if
                    # the verifier returned its own evidence.
                    evidence_list = result.get(
                        "evidence",
                        [],
                    )

                    if isinstance(
                        evidence_list,
                        list,
                    ):
                        for evidence in evidence_list:
                            if isinstance(
                                evidence,
                                dict,
                            ):
                                apply_source_reliability(
                                    evidence
                                )

                # =========================================
                # NLI CONTRADICTION DETECTION
                # =========================================
                nli_summary = None

                if enable_nli:
                    try:
                        with st.spinner(
                            "Running contradiction detection (NLI)..."
                        ):
                            nli_output = (
                                run_nli_pipeline(
                                    verification_results
                                )
                            )

                            verification_results = (
                                nli_output[
                                    "results"
                                ]
                            )

                            nli_summary = (
                                nli_output[
                                    "summary"
                                ]
                            )

                    except Exception as error:
                        st.warning(
                            "NLI contradiction detection "
                            "failed: "
                            f"{error}"
                        )

                # =========================================
                # SOURCE RELIABILITY
                # =========================================
                source_urls = enrich_sources(
                    verification_results
                )

                average_source_reliability = (
                    calculate_average_source_reliability(
                        source_urls
                    )
                    if source_urls
                    else 50.0
                )

                source_badge = get_source_badge(
                    average_source_reliability
                )

                # =========================================
                # TRUST SCORE V1
                # =========================================
                overall_score = safe_float(
                    calculate_overall_score(
                        verification_results
                    ),
                    0.0,
                )

                trust_level = get_trust_level(
                    overall_score
                )

                # =========================================
                # STATUS COUNTS
                # =========================================
                try:
                    status_counts = (
                        count_statuses(
                            verification_results
                        )
                    )

                except Exception:
                    status_counts = {
                        "Verified": 0,
                        "Partially Verified": 0,
                        "Unsupported": 0,
                        "Incorrect": 0,
                    }

                    for result in (
                        verification_results
                    ):
                        status = normalize_status(
                            result.get(
                                "status"
                            )
                        )

                        status_counts[
                            status
                        ] += 1

                # =========================================
                # ADVANCED TRUST SCORE V2
                # =========================================
                trust_metrics = (
                    calculate_trust_metrics_safe(
                        verification_results
                    )
                )

                # Use the real source reliability value
                # when it is available and recompute the
                # final weighted score transparently.
                agreement = (
                    calculate_evidence_agreement(
                        verification_results
                    )
                )

                verifier_score = safe_float(
                    trust_metrics.get(
                        "verifier",
                        0,
                    )
                )

                reranker_score = safe_float(
                    trust_metrics.get(
                        "reranker",
                        0,
                    )
                )

                nli_score = safe_float(
                    trust_metrics.get(
                        "nli",
                        0,
                    )
                )

                if source_urls:
                    source_score = (
                        average_source_reliability
                    )
                else:
                    source_score = safe_float(
                        trust_metrics.get(
                            "source",
                            50,
                        ),
                        50,
                    )

                final_trust_score = (
                    verifier_score * 0.35
                    + reranker_score * 0.25
                    + nli_score * 0.20
                    + source_score * 0.10
                    + agreement * 0.10
                )

                final_trust_score = max(
                    0.0,
                    min(
                        final_trust_score,
                        100.0,
                    ),
                )

                trust_metrics = {
                    "verifier": round(
                        verifier_score,
                        2,
                    ),
                    "reranker": round(
                        reranker_score,
                        2,
                    ),
                    "nli": round(
                        nli_score,
                        2,
                    ),
                    "source": round(
                        source_score,
                        2,
                    ),
                    "agreement": round(
                        agreement,
                        2,
                    ),
                    "final_score": round(
                        final_trust_score,
                        2,
                    ),
                }

                # =========================================
                # FINAL RESPONSE
                # =========================================
                final_verified_response = (
                    build_final_response(
                        verification_results
                    )
                )

                # =========================================
                # DOCUMENT NAME
                # =========================================
                document_names = []

                if uploaded_files:
                    document_names = [
                        uploaded_file.name
                        for uploaded_file
                        in uploaded_files
                    ]

                document_name = (
                    ", ".join(
                        document_names
                    )
                    if document_names
                    else "Web Verification"
                )

                # =========================================
                # CREATE REPORT DATA
                # =========================================
                report_data = create_report_data(
                    question=(
                        verification_question
                    ),
                    document_name=(
                        document_name
                    ),
                    ai_answer=(
                        selected_answer
                    ),
                    overall_score=(
                        overall_score
                    ),
                    trust_level=(
                        trust_level
                    ),
                    verification_results=(
                        verification_results
                    ),
                )

                # =========================================
                # TRUST SCORE V2 DATA
                # =========================================
                report_data[
                    "trust_score_v2"
                ] = trust_metrics

                report_data[
                    "final_trust_score"
                ] = final_trust_score

                report_data[
                    "source_reliability"
                ] = average_source_reliability

                report_data[
                    "source_reliability_badge"
                ] = source_badge

                report_data[
                    "evidence_agreement"
                ] = agreement

                # =========================================
                # COUNT EVIDENCE
                # =========================================
                (
                    pdf_evidence_count,
                    web_evidence_count,
                ) = count_evidence_sources(
                    verification_results
                )

                # =========================================
                # USER METADATA
                # =========================================
                report_data[
                    "generated_by"
                ] = st.session_state.get(
                    "username",
                    "",
                )

                report_data[
                    "user_id"
                ] = st.session_state.get(
                    "user_id"
                )

                report_data[
                    "user_email"
                ] = st.session_state.get(
                    "user_email",
                    "",
                )

                report_data[
                    "user_role"
                ] = st.session_state.get(
                    "user_role",
                    "user",
                )

                # =========================================
                # MODEL INFORMATION
                # =========================================
                report_data[
                    "selected_llm"
                ] = selected_model

                report_data[
                    "llm_comparison_enabled"
                ] = bool(
                    llama_answer
                )

                report_data[
                    "gemini_answer"
                ] = gemini_answer

                report_data[
                    "llama_answer"
                ] = llama_answer

                # =========================================
                # DOCUMENT INFORMATION
                # =========================================
                report_data[
                    "uploaded_documents"
                ] = document_names

                report_data[
                    "total_pdf_pages"
                ] = total_pages

                # =========================================
                # RETRIEVAL INFORMATION
                # =========================================
                report_data[
                    "retrieval_method"
                ] = (
                    "FAISS + BM25 + "
                    "CrossEncoder Reranking"
                    if enable_reranking
                    else "FAISS + BM25 Hybrid"
                )

                report_data[
                    "semantic_search_enabled"
                ] = True

                report_data[
                    "bm25_enabled"
                ] = True

                report_data[
                    "reranking_enabled"
                ] = bool(
                    enable_reranking
                )

                report_data[
                    "hybrid_candidate_count"
                ] = 10

                report_data[
                    "final_pdf_evidence_count_per_claim"
                ] = 5

                report_data[
                    "reranker_model"
                ] = (
                    "cross-encoder/"
                    "ms-marco-MiniLM-L6-v2"
                    if enable_reranking
                    else None
                )

                # =========================================
                # NLI INFORMATION
                # =========================================
                report_data[
                    "nli_enabled"
                ] = bool(
                    enable_nli
                )

                report_data[
                    "nli_summary"
                ] = nli_summary

                # =========================================
                # WEB INFORMATION
                # =========================================
                report_data[
                    "web_verification_enabled"
                ] = bool(
                    enable_web_verification
                )

                report_data[
                    "web_domain_group"
                ] = selected_domain_group

                report_data[
                    "minimum_web_relevance_score"
                ] = minimum_web_score

                # =========================================
                # EVIDENCE COUNTS
                # =========================================
                report_data[
                    "pdf_evidence_count"
                ] = pdf_evidence_count

                report_data[
                    "web_evidence_count"
                ] = web_evidence_count

                report_data[
                    "source_urls"
                ] = source_urls

                # =========================================
                # FINAL RESPONSE
                # =========================================
                report_data[
                    "final_verified_response"
                ] = final_verified_response

                # =========================================
                # JSON SAFE
                # =========================================
                report_data = make_json_safe(
                    report_data
                )

                # =========================================
                # REPORT FILES
                # =========================================
                json_report = create_json_report(
                    report_data
                )

                text_report = create_text_report(
                    report_data
                )

                pdf_report = create_pdf_report(
                    report_data
                )

                # =========================================
                # SAVE TO SUPABASE
                # =========================================
                saved_record_id = (
                    save_verification(
                        report_data=report_data,
                        user_id=st.session_state[
                            "user_id"
                        ],
                        access_token=st.session_state[
                            "access_token"
                        ],
                        refresh_token=st.session_state[
                            "refresh_token"
                        ],
                    )
                )

                # =========================================
                # STORE RESULT IN SESSION
                # =========================================
                st.session_state[
                    "verification_output"
                ] = {
                    "verification_results": (
                        verification_results
                    ),
                    "overall_score": (
                        overall_score
                    ),
                    "trust_level": (
                        trust_level
                    ),
                    "status_counts": (
                        status_counts
                    ),
                    "trust_metrics": (
                        trust_metrics
                    ),
                    "nli_summary": (
                        nli_summary
                    ),
                    "source_reliability": (
                        average_source_reliability
                    ),
                    "source_reliability_badge": (
                        source_badge
                    ),
                    "evidence_agreement": (
                        agreement
                    ),
                    "final_verified_response": (
                        final_verified_response
                    ),
                    "selected_answer": (
                        selected_answer
                    ),
                    "selected_model": (
                        selected_model
                    ),
                    "question": (
                        verification_question
                    ),
                    "report_data": (
                        report_data
                    ),
                    "json_report": (
                        json_report
                    ),
                    "text_report": (
                        text_report
                    ),
                    "pdf_report": (
                        pdf_report
                    ),
                    "saved_record_id": (
                        saved_record_id
                    ),
                    "total_pages": (
                        total_pages
                    ),
                    "pdf_evidence_count": (
                        pdf_evidence_count
                    ),
                    "web_evidence_count": (
                        web_evidence_count
                    ),
                    "reranking_enabled": (
                        enable_reranking
                    ),
                }

                st.success(
                    "Verification completed successfully "
                    f"and saved as Report #{saved_record_id}."
                )

            except Exception as error:
                st.error(
                    "Application error during verification."
                )
                st.code(
                    str(error)
                )


# =========================================================
# DISPLAY VERIFICATION RESULT
# =========================================================
verification_output = st.session_state.get(
    "verification_output"
)

if verification_output:
    st.divider()

    st.write(
        "# 🛡️ Verification Results"
    )

    # =====================================================
    # REPORT INFORMATION
    # =====================================================
    info_col1, info_col2, info_col3 = (
        st.columns(3)
    )

    with info_col1:
        st.metric(
            "Report ID",
            verification_output.get(
                "saved_record_id",
                "-",
            ),
        )

    with info_col2:
        st.metric(
            "PDF Pages",
            verification_output.get(
                "total_pages",
                0,
            ),
        )

    with info_col3:
        st.metric(
            "Selected Model",
            verification_output.get(
                "selected_model",
                "Unknown",
            ),
        )

    # =====================================================
    # QUESTION
    # =====================================================
    st.write(
        "### ❓ Question"
    )

    st.info(
        verification_output.get(
            "question",
            "",
        )
    )

    # =====================================================
    # ORIGINAL AI ANSWER
    # =====================================================
    st.write(
        "### 🤖 Original AI Answer"
    )

    st.write(
        verification_output.get(
            "selected_answer",
            "",
        )
    )

    st.divider()

    # =====================================================
    # TRUST DASHBOARD
    # =====================================================
    st.write(
        "## 📊 Trust Dashboard"
    )

    overall_score = safe_float(
        verification_output.get(
            "overall_score",
            0,
        )
    )

    trust_level = verification_output.get(
        "trust_level",
        "Unknown",
    )

    status_counts = verification_output.get(
        "status_counts",
        {},
    )

    (
        trust_col,
        verified_col,
        partial_col,
        unsupported_col,
        incorrect_col,
    ) = st.columns(5)

    with trust_col:
        st.metric(
            "Trust Score",
            f"{overall_score:.2f}%",
        )

        st.caption(
            f"Trust Level: {trust_level}"
        )

    with verified_col:
        st.metric(
            "✅ Verified",
            status_counts.get(
                "Verified",
                0,
            ),
        )

    with partial_col:
        st.metric(
            "⚠️ Partial",
            status_counts.get(
                "Partially Verified",
                0,
            ),
        )

    with unsupported_col:
        st.metric(
            "❔ Unsupported",
            status_counts.get(
                "Unsupported",
                0,
            ),
        )

    with incorrect_col:
        st.metric(
            "❌ Incorrect",
            status_counts.get(
                "Incorrect",
                0,
            ),
        )

    st.progress(
        max(
            0.0,
            min(
                overall_score / 100,
                1.0,
            ),
        )
    )

    # =====================================================
    # EVIDENCE COUNTS
    # =====================================================
    evidence_col1, evidence_col2 = (
        st.columns(2)
    )

    with evidence_col1:
        st.metric(
            "📄 PDF Evidence",
            verification_output.get(
                "pdf_evidence_count",
                0,
            ),
        )

    with evidence_col2:
        st.metric(
            "🌐 Web Evidence",
            verification_output.get(
                "web_evidence_count",
                0,
            ),
        )

    if verification_output.get(
        "reranking_enabled",
        False,
    ):
        st.success(
            "🧠 Retrieval Pipeline: "
            "FAISS + BM25 + Cross-Encoder Reranking"
        )
    else:
        st.info(
            "🔎 Retrieval Pipeline: "
            "FAISS + BM25 Hybrid Search"
        )

    st.divider()

    # =====================================================
    # ADVANCED TRUST SCORE V2
    # =====================================================
    trust_metrics = verification_output.get(
        "trust_metrics"
    )

    if trust_metrics:
        st.write(
            "## 📈 Advanced Trust Score V2"
        )

        metric_col1, metric_col2, metric_col3 = (
            st.columns(3)
        )

        metric_col1.metric(
            "Verifier",
            f"{safe_float(trust_metrics.get('verifier', 0)):.1f}%",
        )

        metric_col2.metric(
            "Reranker",
            f"{safe_float(trust_metrics.get('reranker', 0)):.1f}%",
        )

        metric_col3.metric(
            "NLI",
            f"{safe_float(trust_metrics.get('nli', 0)):.1f}%",
        )

        metric_col4, metric_col5, metric_col6 = (
            st.columns(3)
        )

        metric_col4.metric(
            "Source Quality",
            f"{safe_float(trust_metrics.get('source', 0)):.1f}%",
        )

        metric_col5.metric(
            "Evidence Agreement",
            f"{safe_float(trust_metrics.get('agreement', 0)):.1f}%",
        )

        metric_col6.metric(
            "Final Trust Score",
            f"{safe_float(trust_metrics.get('final_score', 0)):.1f}%",
        )

        final_score = safe_float(
            trust_metrics.get(
                "final_score",
                0,
            )
        )

        st.progress(
            max(
                0.0,
                min(
                    final_score / 100,
                    1.0,
                ),
            )
        )

        if final_score >= 90:
            st.success(
                "Very High Trust"
            )

        elif final_score >= 75:
            st.info(
                "High Trust"
            )

        elif final_score >= 60:
            st.warning(
                "Moderate Trust"
            )

        else:
            st.error(
                "Low Trust"
            )

        st.divider()

    # =====================================================
    # SOURCE RELIABILITY
    # =====================================================
    source_reliability = safe_float(
        verification_output.get(
            "source_reliability",
            50,
        ),
        50,
    )

    source_badge = verification_output.get(
        "source_reliability_badge",
        get_source_badge(
            source_reliability
        ),
    )

    st.write(
        "## 🌐 Source Reliability"
    )

    source_col1, source_col2 = (
        st.columns(2)
    )

    with source_col1:
        st.metric(
            "Average Source Reliability",
            f"{source_reliability:.1f}/100",
        )

    with source_col2:
        st.metric(
            "Source Quality",
            source_badge,
        )

    # =====================================================
    # NLI SUMMARY
    # =====================================================
    nli_summary = verification_output.get(
        "nli_summary"
    )

    if nli_summary:
        st.write(
            "## ⚖️ NLI Contradiction Summary"
        )

        nli_col1, nli_col2, nli_col3 = (
            st.columns(3)
        )

        nli_col1.metric(
            "Entailment",
            nli_summary.get(
                "entailment_count",
                0,
            ),
        )

        nli_col2.metric(
            "Contradiction",
            nli_summary.get(
                "contradiction_count",
                0,
            ),
        )

        nli_col3.metric(
            "Neutral",
            nli_summary.get(
                "neutral_count",
                0,
            ),
        )

        relation = nli_summary.get(
            "overall_relation",
            "neutral",
        )

        if relation == "entailment":
            st.success(
                "Overall NLI Relation: Evidence supports the claim."
            )

        elif relation == "contradiction":
            st.error(
                "Overall NLI Relation: Evidence contradicts the claim."
            )

        else:
            st.info(
                "Overall NLI Relation: Evidence is neutral or inconclusive."
            )

    st.divider()

    # =====================================================
    # FINAL VERIFIED RESPONSE
    # =====================================================
    st.write(
        "## ✅ Final Verified Response"
    )

    st.success(
        verification_output.get(
            "final_verified_response",
            "",
        )
    )

    st.divider()

    # =====================================================
    # CLAIM BY CLAIM
    # =====================================================
    st.write(
        "## 🔍 Claim-by-Claim Verification"
    )

    verification_results = (
        verification_output.get(
            "verification_results",
            [],
        )
    )

    for claim_number, result in enumerate(
        verification_results,
        start=1,
    ):
        with st.container(
            border=True
        ):
            st.write(
                f"### Claim {claim_number}"
            )

            claim_text = result.get(
                "claim",
                "Claim unavailable.",
            )

            st.write(
                claim_text
            )

            # =============================================
            # STATUS
            # =============================================
            status = normalize_status(
                result.get(
                    "status"
                )
            )

            display_verification_status(
                status
            )

            # =============================================
            # CONFIDENCE
            # =============================================
            confidence_score = (
                safe_confidence_score(
                    result.get(
                        "confidence_score",
                        0,
                    )
                )
            )

            st.write(
                f"**Confidence Score:** "
                f"{confidence_score:.2f}%"
            )

            # =============================================
            # EXPLANATION
            # =============================================
            explanation = result.get(
                "explanation",
                "",
            )

            if explanation:
                st.write(
                    "**Explanation:**"
                )

                st.write(
                    explanation
                )

            # =============================================
            # SUPPORTING EVIDENCE
            # =============================================
            selected_support = (
                get_selected_supporting_evidence(
                    result
                )
            )

            if selected_support:
                st.write(
                    "**Selected Supporting Evidence:**"
                )

                st.info(
                    selected_support
                )

            # =============================================
            # EVIDENCE
            # =============================================
            evidence_list = result.get(
                "evidence",
                [],
            )

            if evidence_list:
                with st.expander(
                    "📚 View Evidence Scores, NLI & Reranking"
                ):
                    for (
                        evidence_number,
                        evidence,
                    ) in enumerate(
                        evidence_list,
                        start=1,
                    ):
                        if not isinstance(
                            evidence,
                            dict,
                        ):
                            continue

                        display_evidence_item(
                            evidence=evidence,
                            evidence_number=evidence_number,
                        )

                        if (
                            evidence_number
                            < len(
                                evidence_list
                            )
                        ):
                            st.divider()

    st.divider()

    # =====================================================
    # DOWNLOAD REPORTS
    # =====================================================
    st.write(
        "## 📥 Download Verification Report"
    )

    (
        download_pdf_col,
        download_json_col,
        download_txt_col,
    ) = st.columns(3)

    with download_pdf_col:
        st.download_button(
            label="📄 Download PDF",
            data=verification_output.get(
                "pdf_report",
                b"",
            ),
            file_name=(
                "trustguard_verification_report.pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
        )

    with download_json_col:
        st.download_button(
            label="🧾 Download JSON",
            data=verification_output.get(
                "json_report",
                "",
            ),
            file_name=(
                "trustguard_verification_report.json"
            ),
            mime="application/json",
            use_container_width=True,
        )

    with download_txt_col:
        st.download_button(
            label="📝 Download TXT",
            data=verification_output.get(
                "text_report",
                "",
            ),
            file_name=(
                "trustguard_verification_report.txt"
            ),
            mime="text/plain",
            use_container_width=True,
        )


# =========================================================
# FOOTER
# =========================================================
st.divider()

st.caption(
    "TrustGuard AI • Hallucination Detection • "
    "FAISS • BM25 • Cross-Encoder • NLI • "
    "Source Reliability • Web Verification • Supabase"
)