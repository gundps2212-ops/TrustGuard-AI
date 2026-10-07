from __future__ import annotations

from typing import Any

import numpy as np
import torch

from sentence_transformers import CrossEncoder


# =========================================================
# CONFIGURATION
# =========================================================

RERANKER_MODEL_NAME = (
    "cross-encoder/ms-marco-MiniLM-L6-v2"
)

DEFAULT_FINAL_TOP_K = 5


# =========================================================
# MODEL CACHE
# =========================================================

_reranker_model = None


def get_reranker_model() -> CrossEncoder:
    """
    Load CrossEncoder only once.

    Sigmoid converts MS-MARCO logits
    into scores between 0 and 1.
    """

    global _reranker_model

    if _reranker_model is None:

        _reranker_model = CrossEncoder(
            RERANKER_MODEL_NAME,
            activation_fn=(
                torch.nn.Sigmoid()
            ),
        )

    return _reranker_model


# =========================================================
# HELPERS
# =========================================================

def clean_text(
    value: Any,
) -> str:
    """
    Convert value to clean string.
    """

    return str(
        value or ""
    ).strip()


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Safely convert to float.
    """

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def get_evidence_text(
    evidence: dict[str, Any],
) -> str:
    """
    Get main text from evidence item.
    """

    return clean_text(
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


# =========================================================
# CROSS-ENCODER RERANKING
# =========================================================

def rerank_evidence(
    query: str,
    evidence_items: list[dict[str, Any]],
    top_k: int = DEFAULT_FINAL_TOP_K,
) -> list[dict[str, Any]]:
    """
    Rerank retrieved evidence using CrossEncoder.

    Input:
        Hybrid retrieval results.

    Output:
        Evidence sorted by reranker relevance.
    """

    clean_query = clean_text(
        query
    )

    if not clean_query:
        return []

    if not evidence_items:
        return []

    valid_items = []

    text_pairs = []


    # =====================================================
    # CREATE QUERY-DOCUMENT PAIRS
    # =====================================================

    for evidence in evidence_items:

        if not isinstance(
            evidence,
            dict,
        ):
            continue

        evidence_text = (
            get_evidence_text(
                evidence
            )
        )

        if not evidence_text:
            continue

        valid_items.append(
            dict(evidence)
        )

        text_pairs.append(
            [
                clean_query,
                evidence_text,
            ]
        )


    if not valid_items:
        return []


    # =====================================================
    # LOAD RERANKER
    # =====================================================

    model = get_reranker_model()


    # =====================================================
    # PREDICT RELEVANCE
    # =====================================================

    scores = model.predict(
        text_pairs,
        batch_size=16,
        show_progress_bar=False,
    )


    scores = np.asarray(
        scores,
        dtype=np.float32,
    ).reshape(-1)


    # =====================================================
    # ADD SCORES
    # =====================================================

    for index, evidence in enumerate(
        valid_items
    ):

        reranker_score = safe_float(
            scores[index],
            0.0,
        )

        evidence[
            "reranker_score"
        ] = round(
            reranker_score,
            4,
        )

        evidence[
            "pre_rerank_rank"
        ] = evidence.get(
            "retrieval_rank",
            index + 1,
        )

        evidence[
            "reranking_method"
        ] = (
            "CrossEncoder"
        )


    # =====================================================
    # SORT HIGHEST SCORE FIRST
    # =====================================================

    valid_items.sort(
        key=lambda item: (
            safe_float(
                item.get(
                    "reranker_score",
                    0,
                )
            )
        ),
        reverse=True,
    )


    # =====================================================
    # ADD FINAL RANK
    # =====================================================

    safe_top_k = max(
        1,
        min(
            int(top_k),
            len(valid_items),
        ),
    )


    final_results = (
        valid_items[
            :safe_top_k
        ]
    )


    for final_rank, evidence in enumerate(
        final_results,
        start=1,
    ):

        evidence[
            "final_rank"
        ] = final_rank

        evidence[
            "retrieval_pipeline"
        ] = (
            "FAISS + BM25 + CrossEncoder"
        )


    return final_results