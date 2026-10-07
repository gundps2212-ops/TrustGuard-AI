from __future__ import annotations

from typing import Any

import numpy as np
from sentence_transformers import CrossEncoder


# =========================================================
# CONFIGURATION
# =========================================================

# Lightweight NLI model
# Faster than nli-deberta-v3-base
NLI_MODEL_NAME = "cross-encoder/nli-MiniLM2-L6-H768"

# Maximum characters taken from one evidence item
MAX_EVIDENCE_CHARS = 1200

# Maximum evidence items processed for one claim
MAX_EVIDENCE_ITEMS = 8

# Batch size
NLI_BATCH_SIZE = 4

# Maximum transformer tokens
NLI_MAX_LENGTH = 256


# Model output order
LABEL_MAPPING = [
    "contradiction",
    "entailment",
    "neutral",
]


# =========================================================
# GLOBAL MODEL
# =========================================================

_nli_model = None


# =========================================================
# LOAD MODEL
# =========================================================

def get_nli_model() -> CrossEncoder:
    """
    Load NLI model only once.

    The model is loaded lazily.
    """

    global _nli_model

    if _nli_model is None:

        print(
            f"[TrustGuard AI] Loading NLI model: "
            f"{NLI_MODEL_NAME}"
        )

        _nli_model = CrossEncoder(
            NLI_MODEL_NAME,
            max_length=NLI_MAX_LENGTH,
        )

        print(
            "[TrustGuard AI] NLI model loaded successfully."
        )

    return _nli_model


# =========================================================
# TEXT HELPERS
# =========================================================

def clean_text(
    value: Any,
) -> str:
    """
    Convert any value to clean string.
    """

    if value is None:
        return ""

    try:
        text = str(value).strip()
    except Exception:
        return ""

    return text


def truncate_text(
    text: str,
    max_chars: int = MAX_EVIDENCE_CHARS,
) -> str:
    """
    Limit evidence size.

    Long PDF chunks can make NLI very slow.
    """

    text = clean_text(text)

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "..."


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


# =========================================================
# EVIDENCE TEXT
# =========================================================

def get_evidence_text(
    evidence: dict[str, Any],
) -> str:
    """
    Extract evidence text from different formats.
    """

    if not isinstance(evidence, dict):
        return ""

    text = evidence.get("text")

    if not text:
        text = evidence.get("content")

    if not text:
        text = evidence.get("snippet")

    if not text:
        text = evidence.get("page_content")

    return truncate_text(
        clean_text(text)
    )


# =========================================================
# EMPTY NLI RESULT
# =========================================================

def empty_nli_result() -> dict[str, Any]:
    """
    Return safe neutral result.
    """

    return {
        "label": "neutral",
        "confidence": 0.0,
        "contradiction_score": 0.0,
        "entailment_score": 0.0,
        "neutral_score": 1.0,
    }


# =========================================================
# CONVERT MODEL SCORES
# =========================================================

def build_nli_result(
    probabilities: Any,
) -> dict[str, Any]:
    """
    Convert model probabilities into TrustGuard format.
    """

    probabilities = np.asarray(
        probabilities,
        dtype=np.float32,
    ).flatten()

    # Safety check
    if len(probabilities) < 3:
        return empty_nli_result()

    contradiction_score = safe_float(
        probabilities[0]
    )

    entailment_score = safe_float(
        probabilities[1]
    )

    neutral_score = safe_float(
        probabilities[2]
    )

    highest_index = int(
        np.argmax(probabilities[:3])
    )

    label = LABEL_MAPPING[
        highest_index
    ]

    confidence = safe_float(
        probabilities[highest_index]
    )

    return {
        "label": label,

        "confidence": round(
            confidence,
            4,
        ),

        "contradiction_score": round(
            contradiction_score,
            4,
        ),

        "entailment_score": round(
            entailment_score,
            4,
        ),

        "neutral_score": round(
            neutral_score,
            4,
        ),
    }


# =========================================================
# SINGLE CLAIM + EVIDENCE
# =========================================================

def detect_nli_relation(
    claim: str,
    evidence_text: str,
) -> dict[str, Any]:
    """
    Compare one evidence text against one claim.

    Evidence = premise
    Claim = hypothesis
    """

    clean_claim = clean_text(
        claim
    )

    clean_evidence = truncate_text(
        clean_text(evidence_text)
    )

    if not clean_claim:
        return empty_nli_result()

    if not clean_evidence:
        return empty_nli_result()

    try:

        model = get_nli_model()

        scores = model.predict(
            [
                (
                    clean_evidence,
                    clean_claim,
                )
            ],
            batch_size=1,
            apply_softmax=True,
            show_progress_bar=False,
        )

        scores = np.asarray(
            scores,
            dtype=np.float32,
        )

        if scores.ndim == 2:
            probabilities = scores[0]
        else:
            probabilities = scores

        return build_nli_result(
            probabilities
        )

    except Exception as error:

        print(
            "[TrustGuard AI] NLI error:",
            error,
        )

        return empty_nli_result()


# =========================================================
# MULTIPLE EVIDENCE ITEMS
# =========================================================

def analyze_evidence_nli(
    claim: str,
    evidence_items: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:
    """
    Run NLI for multiple evidence items.

    Optimizations:
    - Limits evidence count
    - Limits text length
    - Batch inference
    - Reuses loaded model
    """

    clean_claim = clean_text(
        claim
    )

    if not clean_claim:
        return evidence_items

    if not evidence_items:
        return []

    # -----------------------------------------------------
    # LIMIT NUMBER OF EVIDENCE ITEMS
    # -----------------------------------------------------

    evidence_items = evidence_items[
        :MAX_EVIDENCE_ITEMS
    ]

    valid_items = []

    sentence_pairs = []

    # -----------------------------------------------------
    # PREPARE EVIDENCE
    # -----------------------------------------------------

    for evidence in evidence_items:

        if not isinstance(
            evidence,
            dict,
        ):
            continue

        evidence_copy = dict(
            evidence
        )

        evidence_text = get_evidence_text(
            evidence_copy
        )

        if not evidence_text:
            continue

        valid_items.append(
            evidence_copy
        )

        sentence_pairs.append(
            (
                evidence_text,
                clean_claim,
            )
        )

    if not valid_items:
        return []

    # -----------------------------------------------------
    # LOAD MODEL
    # -----------------------------------------------------

    try:

        model = get_nli_model()

        # -------------------------------------------------
        # BATCH PREDICTION
        # -------------------------------------------------

        score_matrix = model.predict(
            sentence_pairs,
            batch_size=NLI_BATCH_SIZE,
            show_progress_bar=False,
            apply_softmax=True,
        )

        score_matrix = np.asarray(
            score_matrix,
            dtype=np.float32,
        )

        # -------------------------------------------------
        # SAFETY
        # -------------------------------------------------

        if score_matrix.ndim == 1:

            score_matrix = np.expand_dims(
                score_matrix,
                axis=0,
            )

        # -------------------------------------------------
        # ADD RESULTS
        # -------------------------------------------------

        for index, evidence in enumerate(
            valid_items
        ):

            if index >= len(
                score_matrix
            ):
                break

            result = build_nli_result(
                score_matrix[index]
            )

            evidence[
                "nli_label"
            ] = result["label"]

            evidence[
                "nli_confidence"
            ] = result[
                "confidence"
            ]

            evidence[
                "contradiction_score"
            ] = result[
                "contradiction_score"
            ]

            evidence[
                "entailment_score"
            ] = result[
                "entailment_score"
            ]

            evidence[
                "neutral_score"
            ] = result[
                "neutral_score"
            ]

            evidence[
                "nli_model"
            ] = NLI_MODEL_NAME

        return valid_items

    except Exception as error:

        print(
            "[TrustGuard AI] "
            "Batch NLI error:",
            error,
        )

        # If model fails, return evidence
        # with neutral NLI results.

        for evidence in valid_items:

            result = empty_nli_result()

            evidence[
                "nli_label"
            ] = result["label"]

            evidence[
                "nli_confidence"
            ] = result["confidence"]

            evidence[
                "contradiction_score"
            ] = result[
                "contradiction_score"
            ]

            evidence[
                "entailment_score"
            ] = result[
                "entailment_score"
            ]

            evidence[
                "neutral_score"
            ] = result[
                "neutral_score"
            ]

            evidence[
                "nli_model"
            ] = NLI_MODEL_NAME

        return valid_items


# =========================================================
# CLAIM LEVEL SUMMARY
# =========================================================

def create_nli_summary(
    evidence_items: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    """
    Create one NLI summary for a claim.
    """

    if not evidence_items:

        return {
            "overall_relation": "neutral",
            "strongest_entailment": 0.0,
            "strongest_contradiction": 0.0,
            "strongest_neutral": 0.0,
            "entailment_count": 0,
            "contradiction_count": 0,
            "neutral_count": 0,
        }

    strongest_entailment = 0.0

    strongest_contradiction = 0.0

    strongest_neutral = 0.0

    entailment_count = 0

    contradiction_count = 0

    neutral_count = 0

    # -----------------------------------------------------
    # ANALYZE RESULTS
    # -----------------------------------------------------

    for evidence in evidence_items:

        if not isinstance(
            evidence,
            dict,
        ):
            continue

        entailment_score = safe_float(
            evidence.get(
                "entailment_score",
                0.0,
            )
        )

        contradiction_score = safe_float(
            evidence.get(
                "contradiction_score",
                0.0,
            )
        )

        neutral_score = safe_float(
            evidence.get(
                "neutral_score",
                0.0,
            )
        )

        strongest_entailment = max(
            strongest_entailment,
            entailment_score,
        )

        strongest_contradiction = max(
            strongest_contradiction,
            contradiction_score,
        )

        strongest_neutral = max(
            strongest_neutral,
            neutral_score,
        )

        label = evidence.get(
            "nli_label",
            "neutral",
        )

        if label == "entailment":

            entailment_count += 1

        elif label == "contradiction":

            contradiction_count += 1

        else:

            neutral_count += 1

    # -----------------------------------------------------
    # DETERMINE OVERALL RELATION
    # -----------------------------------------------------

    if (
        strongest_contradiction
        >= 0.60
        and strongest_contradiction
        > strongest_entailment
    ):

        overall_relation = (
            "contradiction"
        )

    elif (
        strongest_entailment
        >= 0.60
        and strongest_entailment
        >= strongest_contradiction
    ):

        overall_relation = (
            "entailment"
        )

    else:

        overall_relation = (
            "neutral"
        )

    # -----------------------------------------------------
    # RETURN SUMMARY
    # -----------------------------------------------------

    return {
        "overall_relation": (
            overall_relation
        ),

        "strongest_entailment": round(
            strongest_entailment,
            4,
        ),

        "strongest_contradiction": round(
            strongest_contradiction,
            4,
        ),

        "strongest_neutral": round(
            strongest_neutral,
            4,
        ),

        "entailment_count": (
            entailment_count
        ),

        "contradiction_count": (
            contradiction_count
        ),

        "neutral_count": (
            neutral_count
        ),
    }


# =========================================================
# MODEL STATUS
# =========================================================

def is_nli_model_loaded() -> bool:
    """
    Check whether NLI model is already loaded.
    """

    return _nli_model is not None


def reset_nli_model() -> None:
    """
    Reset model from memory.
    """

    global _nli_model

    _nli_model = None


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print(
        "Testing TrustGuard AI NLI..."
    )

    claim = (
        "India is the largest democracy "
        "in the world."
    )

    evidence = (
        "India is the world's largest "
        "democracy."
    )

    result = detect_nli_relation(
        claim,
        evidence,
    )

    print(
        "NLI RESULT:"
    )

    print(result)

    print(
        "NLI test completed."
    )