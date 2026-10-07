from __future__ import annotations

from typing import Any


# =========================================================
# HELPERS
# =========================================================

def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp_score(score: float) -> float:
    return max(0.0, min(score, 100.0))


# =========================================================
# VERIFIER SCORE
# =========================================================

def verifier_score(
    verification_results: list[dict[str, Any]],
) -> float:
    if not verification_results:
        return 0.0

    total = 0.0

    for result in verification_results:
        total += safe_float(
            result.get(
                "confidence_score",
                0,
            )
        )

    return total / len(verification_results)


# =========================================================
# RERANKER SCORE
# =========================================================

def reranker_score(
    verification_results: list[dict[str, Any]],
) -> float:
    scores = []

    for result in verification_results:
        for evidence in result.get("evidence", []):
            score = evidence.get(
                "reranker_score"
            )
            if score is not None:
                scores.append(
                    safe_float(score) * 100
                )

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


# =========================================================
# NLI SCORE
# =========================================================

def nli_score(
    verification_results: list[dict[str, Any]],
) -> float:
    scores = []

    for result in verification_results:
        for evidence in result.get("evidence", []):
            score = evidence.get(
                "entailment_score"
            )
            if score is not None:
                scores.append(
                    safe_float(score) * 100
                )

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


# =========================================================
# SOURCE QUALITY SCORE
# =========================================================

SOURCE_WEIGHTS = {
    "government": 100,
    "research": 95,
    "university": 90,
    "official": 90,
    "news": 80,
    "wikipedia": 70,
    "web": 60,
    "unknown": 50,
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

    if ".gov" in domain or "government" in source_name:
        return SOURCE_WEIGHTS["government"]

    if "university" in source_name or ".edu" in domain:
        return SOURCE_WEIGHTS["university"]

    if "research" in source_name or "journal" in source_name:
        return SOURCE_WEIGHTS["research"]

    if "official" in source_name:
        return SOURCE_WEIGHTS["official"]

    if "news" in source_name or "reuters" in domain:
        return SOURCE_WEIGHTS["news"]

    if "wikipedia" in domain:
        return SOURCE_WEIGHTS["wikipedia"]

    if domain:
        return SOURCE_WEIGHTS["web"]

    return SOURCE_WEIGHTS["unknown"]


def source_quality_score(
    verification_results: list[dict[str, Any]],
) -> float:
    scores = []

    for result in verification_results:
        for evidence in result.get("evidence", []):
            scores.append(
                detect_source_weight(evidence)
            )

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


# =========================================================
# EVIDENCE AGREEMENT SCORE
# =========================================================

def evidence_agreement_score(
    verification_results: list[dict[str, Any]],
) -> float:
    agreement_scores = []

    for result in verification_results:
        evidence_items = result.get("evidence", [])

        if not evidence_items:
            continue

        support = 0
        contradiction = 0
        neutral = 0

        for evidence in evidence_items:
            label = evidence.get(
                "nli_label",
                "neutral",
            )

            if label == "entailment":
                support += 1
            elif label == "contradiction":
                contradiction += 1
            else:
                neutral += 1

        total = support + contradiction + neutral

        if total == 0:
            continue

        score = (
            support / total
        ) * 100

        agreement_scores.append(score)

    if not agreement_scores:
        return 0.0

    return sum(agreement_scores) / len(agreement_scores)


# =========================================================
# FINAL TRUST SCORE V2
# =========================================================

def calculate_trust_score_v2(
    verification_results: list[dict[str, Any]],
) -> dict[str, float]:

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

    final_score = (
        0.35 * verifier
        + 0.25 * reranker
        + 0.20 * nli
        + 0.10 * source
        + 0.10 * agreement
    )

    final_score = clamp_score(
        final_score
    )

    return {
        "verifier": round(verifier, 2),
        "reranker": round(reranker, 2),
        "nli": round(nli, 2),
        "source": round(source, 2),
        "agreement": round(agreement, 2),
        "final_score": round(final_score, 2),
    }
