from __future__ import annotations

from typing import Any


# =========================================================
# HELPERS
# =========================================================

def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Safely convert a value to float.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp_score(
    score: float,
) -> float:
    """
    Keep score between 0 and 100.
    """
    return max(
        0.0,
        min(float(score), 100.0),
    )


def normalize_score(
    value: Any,
    default: float | None = None,
) -> float | None:
    """
    Convert score to 0-100 format.

    Examples:
        0.95  -> 95
        95    -> 95
        1.0   -> 100
        None  -> None
    """

    if value is None:
        return default

    try:
        score = float(value)
    except (TypeError, ValueError):
        return default

    # Score is probably 0-1
    if 0.0 <= score <= 1.0:
        score *= 100.0

    return clamp_score(score)


def get_evidence(
    verification_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Collect all evidence items safely.
    """

    evidence_items: list[dict[str, Any]] = []

    for result in verification_results:
        items = result.get(
            "evidence",
            [],
        )

        if not isinstance(items, list):
            continue

        for evidence in items:
            if isinstance(evidence, dict):
                evidence_items.append(evidence)

    return evidence_items


# =========================================================
# VERIFIER SCORE
# =========================================================

def verifier_score(
    verification_results: list[dict[str, Any]],
) -> float | None:
    """
    Calculate average verifier confidence.

    Supports both:
        0.95
        95
    """

    scores: list[float] = []

    for result in verification_results:

        value = result.get(
            "confidence_score"
        )

        # Some pipelines may use confidence
        if value is None:
            value = result.get(
                "confidence"
            )

        score = normalize_score(
            value
        )

        if score is not None:
            scores.append(score)

    if not scores:
        return None

    return sum(scores) / len(scores)


# =========================================================
# RERANKER SCORE
# =========================================================

def reranker_score(
    verification_results: list[dict[str, Any]],
) -> float | None:
    """
    Calculate average reranker score.
    """

    scores: list[float] = []

    for evidence in get_evidence(
        verification_results
    ):

        value = evidence.get(
            "reranker_score"
        )

        # fallback names
        if value is None:
            value = evidence.get(
                "rerank_score"
            )

        if value is None:
            value = evidence.get(
                "cross_encoder_score"
            )

        score = normalize_score(
            value
        )

        if score is not None:
            scores.append(score)

    if not scores:
        return None

    return sum(scores) / len(scores)


# =========================================================
# NLI SCORE
# =========================================================

def nli_score(
    verification_results: list[dict[str, Any]],
) -> float | None:
    """
    Calculate average NLI entailment score.

    Supports:
        entailment_score
        nli_score
        confidence_score

    NLI is optional.
    If NLI is disabled/missing, this returns None
    instead of reducing the final score to zero.
    """

    scores: list[float] = []

    for evidence in get_evidence(
        verification_results
    ):

        value = evidence.get(
            "entailment_score"
        )

        if value is None:
            value = evidence.get(
                "nli_score"
            )

        if value is None:
            value = evidence.get(
                "entailment_confidence"
            )

        score = normalize_score(
            value
        )

        if score is not None:
            scores.append(score)

    if not scores:
        return None

    return sum(scores) / len(scores)


# =========================================================
# SOURCE QUALITY
# =========================================================

SOURCE_WEIGHTS = {
    "government": 100.0,
    "research": 95.0,
    "university": 90.0,
    "official": 90.0,
    "news": 80.0,
    "wikipedia": 70.0,
    "web": 60.0,
    "unknown": 50.0,
}


def detect_source_weight(
    evidence: dict[str, Any],
) -> float:

    source_name = str(
        evidence.get(
            "source_name",
            "",
        )
    ).lower()

    domain = str(
        evidence.get(
            "domain",
            "",
        )
    ).lower()

    url = str(
        evidence.get(
            "url",
            "",
        )
    ).lower()

    combined = (
        source_name
        + " "
        + domain
        + " "
        + url
    )

    # Government
    if (
        ".gov" in combined
        or "government" in combined
    ):
        return SOURCE_WEIGHTS[
            "government"
        ]

    # Research / journals
    if (
        "research" in combined
        or "journal" in combined
        or "arxiv" in combined
        or "pubmed" in combined
    ):
        return SOURCE_WEIGHTS[
            "research"
        ]

    # University
    if (
        ".edu" in combined
        or "university" in combined
        or "college" in combined
    ):
        return SOURCE_WEIGHTS[
            "university"
        ]

    # Official
    if "official" in combined:
        return SOURCE_WEIGHTS[
            "official"
        ]

    # News
    if (
        "news" in combined
        or "reuters" in combined
        or "bbc" in combined
        or "cnn" in combined
    ):
        return SOURCE_WEIGHTS[
            "news"
        ]

    # Wikipedia
    if "wikipedia" in combined:
        return SOURCE_WEIGHTS[
            "wikipedia"
        ]

    # Any known domain
    if domain or url:
        return SOURCE_WEIGHTS[
            "web"
        ]

    return SOURCE_WEIGHTS[
        "unknown"
    ]


def source_quality_score(
    verification_results: list[dict[str, Any]],
) -> float | None:

    scores: list[float] = []

    for evidence in get_evidence(
        verification_results
    ):
        scores.append(
            detect_source_weight(
                evidence
            )
        )

    if not scores:
        return None

    return sum(scores) / len(scores)


# =========================================================
# EVIDENCE AGREEMENT SCORE
# =========================================================

def evidence_agreement_score(
    verification_results: list[dict[str, Any]],
) -> float | None:

    agreement_scores: list[float] = []

    for result in verification_results:

        evidence_items = result.get(
            "evidence",
            [],
        )

        if not isinstance(
            evidence_items,
            list,
        ):
            continue

        support = 0
        contradiction = 0
        neutral = 0

        for evidence in evidence_items:

            label = str(
                evidence.get(
                    "nli_label",
                    evidence.get(
                        "label",
                        "neutral",
                    ),
                )
            ).lower()

            if label in (
                "entailment",
                "supported",
                "support",
            ):
                support += 1

            elif label in (
                "contradiction",
                "contradicted",
            ):
                contradiction += 1

            else:
                neutral += 1

        total = (
            support
            + contradiction
            + neutral
        )

        if total == 0:
            continue

        # Positive evidence increases score.
        # Contradictions reduce score.
        agreement = (
            (
                support
                + (0.5 * neutral)
            )
            / total
        ) * 100.0

        # Explicit contradictions should have
        # a stronger negative effect.
        if contradiction > 0:
            contradiction_penalty = (
                contradiction / total
            ) * 25.0

            agreement -= (
                contradiction_penalty
            )

        agreement_scores.append(
            clamp_score(
                agreement
            )
        )

    if not agreement_scores:
        return None

    return (
        sum(agreement_scores)
        / len(agreement_scores)
    )


# =========================================================
# CLAIM STATUS SCORE
# =========================================================

def claim_status_score(
    verification_results: list[dict[str, Any]],
) -> float | None:

    if not verification_results:
        return None

    scores: list[float] = []

    for result in verification_results:

        status = str(
            result.get(
                "status",
                result.get(
                    "verification_status",
                    "",
                ),
            )
        ).lower()

        if status in (
            "verified",
            "supported",
            "entailment",
            "true",
        ):
            scores.append(100.0)

        elif status in (
            "uncertain",
            "neutral",
            "unknown",
        ):
            scores.append(50.0)

        elif status in (
            "contradicted",
            "contradiction",
            "false",
            "unsupported",
        ):
            scores.append(0.0)

    if not scores:
        return None

    return sum(scores) / len(scores)


# =========================================================
# FINAL TRUST SCORE V2
# =========================================================

def calculate_trust_score_v2(
    verification_results: list[dict[str, Any]],
) -> dict[str, float]:

    """
    Calculate TrustGuard AI Advanced Trust Score V2.

    Important improvement:
    Missing/disabled components are NOT automatically
    treated as zero.

    Example:
        If NLI is disabled, NLI is excluded from
        the weighted average instead of reducing
        the final score.
    """

    if not verification_results:
        return {
            "verifier": 0.0,
            "reranker": 0.0,
            "nli": 0.0,
            "source": 0.0,
            "agreement": 0.0,
            "claim_status": 0.0,
            "final_score": 0.0,
        }

    verifier = verifier_score(
        verification_results
    )

    reranker = reranker_score(
        verification_results
    )

    nli = nli_score(
        verification_results
    )

    source = source_quality_score(
        verification_results
    )

    agreement = evidence_agreement_score(
        verification_results
    )

    claim_status = claim_status_score(
        verification_results
    )

    # =====================================================
    # WEIGHTS
    # =====================================================

    weights = {
        "verifier": 0.30,
        "reranker": 0.20,
        "nli": 0.20,
        "source": 0.10,
        "agreement": 0.10,
        "claim_status": 0.10,
    }

    values = {
        "verifier": verifier,
        "reranker": reranker,
        "nli": nli,
        "source": source,
        "agreement": agreement,
        "claim_status": claim_status,
    }

    # =====================================================
    # DYNAMIC WEIGHTING
    # =====================================================
    #
    # Only components that actually have data
    # participate in the final score.
    #

    weighted_total = 0.0
    active_weight = 0.0

    for name, weight in weights.items():

        value = values.get(
            name
        )

        if value is None:
            continue

        weighted_total += (
            value * weight
        )

        active_weight += weight

    if active_weight > 0:

        final_score = (
            weighted_total
            / active_weight
        )

    else:
        final_score = 0.0

    final_score = clamp_score(
        final_score
    )

    # =====================================================
    # RETURN
    # =====================================================

    return {
        "verifier": round(
            verifier or 0.0,
            2,
        ),

        "reranker": round(
            reranker or 0.0,
            2,
        ),

        "nli": round(
            nli or 0.0,
            2,
        ),

        "source": round(
            source or 0.0,
            2,
        ),

        "agreement": round(
            agreement or 0.0,
            2,
        ),

        "claim_status": round(
            claim_status or 0.0,
            2,
        ),

        "final_score": round(
            final_score,
            2,
        ),
    }


# =========================================================
# TRUST LEVEL
# =========================================================

def get_trust_level(
    score: float,
) -> str:

    score = clamp_score(
        safe_float(score)
    )

    if score >= 90:
        return "Very High"

    if score >= 75:
        return "High"

    if score >= 60:
        return "Moderate"

    if score >= 40:
        return "Low"

    return "Very Low"


# =========================================================
# TRUST LEVEL EMOJI
# =========================================================

def get_trust_badge(
    score: float,
) -> str:

    level = get_trust_level(
        score
    )

    if level == "Very High":
        return "🟢 Very High"

    if level == "High":
        return "🟢 High"

    if level == "Moderate":
        return "🟡 Moderate"

    if level == "Low":
        return "🟠 Low"

    return "🔴 Very Low"