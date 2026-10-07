from __future__ import annotations

import re
from typing import Any

import faiss
import numpy as np

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


# =========================================================
# CONFIGURATION
# =========================================================

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

CHUNK_SIZE = 900

CHUNK_OVERLAP = 150

SEMANTIC_WEIGHT = 0.65

BM25_WEIGHT = 0.35


# =========================================================
# LOAD EMBEDDING MODEL
# =========================================================

_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    """
    Load SentenceTransformer model only once.
    """

    global _embedding_model

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_NAME
        )

    return _embedding_model


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(
    text: str,
) -> str:
    """
    Normalize whitespace.
    """

    text = str(
        text or ""
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# =========================================================
# BM25 TOKENIZER
# =========================================================

def tokenize_text(
    text: str,
) -> list[str]:
    """
    Simple tokenizer for BM25 lexical search.
    """

    text = clean_text(
        text
    ).lower()

    tokens = re.findall(
        r"\b[a-zA-Z0-9]+\b",
        text,
    )

    return tokens


# =========================================================
# CREATE CHUNKS
# =========================================================

def split_text_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Split page text into overlapping chunks.
    """

    text = clean_text(
        text
    )

    if not text:
        return []

    if len(text) <= chunk_size:
        return [
            text
        ]

    chunks = []

    start = 0

    text_length = len(
        text
    )

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length,
        )

        chunk = text[
            start:end
        ].strip()

        if chunk:
            chunks.append(
                chunk
            )

        if end >= text_length:
            break

        next_start = (
            end - overlap
        )

        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


# =========================================================
# SCORE NORMALIZATION
# =========================================================

def normalize_scores(
    scores: np.ndarray,
) -> np.ndarray:
    """
    Normalize values to 0-1 range.
    """

    scores = np.asarray(
        scores,
        dtype=np.float32,
    )

    if scores.size == 0:
        return scores

    minimum = float(
        np.min(scores)
    )

    maximum = float(
        np.max(scores)
    )

    if abs(
        maximum - minimum
    ) < 1e-12:

        if maximum > 0:
            return np.ones_like(
                scores,
                dtype=np.float32,
            )

        return np.zeros_like(
            scores,
            dtype=np.float32,
        )

    return (
        scores - minimum
    ) / (
        maximum - minimum
    )


# =========================================================
# BUILD HYBRID INDEX
# =========================================================

def build_evidence_index(
    page_records: list[dict[str, Any]],
):
    """
    Build:
    1. document chunks
    2. FAISS semantic index
    3. BM25 lexical index

    page_records example:

    {
        "document": "sample.pdf",
        "page": 2,
        "text": "..."
    }
    """

    chunks: list[
        dict[str, Any]
    ] = []

    for page_record in page_records:

        document_name = str(
            page_record.get(
                "document",
                "Unknown Document",
            )
        )

        page_number = page_record.get(
            "page",
            0,
        )

        page_text = clean_text(
            page_record.get(
                "text",
                "",
            )
        )

        if not page_text:
            continue

        page_chunks = (
            split_text_into_chunks(
                page_text
            )
        )

        for chunk_number, chunk_text in enumerate(
            page_chunks,
            start=1,
        ):

            chunks.append(
                {
                    "text": chunk_text,

                    "document": (
                        document_name
                    ),

                    "page": (
                        page_number
                    ),

                    "chunk_number": (
                        chunk_number
                    ),
                }
            )

    if not chunks:
        return (
            [],
            None,
        )

    # =====================================================
    # SEMANTIC EMBEDDINGS
    # =====================================================

    model = get_embedding_model()

    chunk_texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = model.encode(
        chunk_texts,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    # Normalize vectors so IndexFlatIP behaves
    # like cosine similarity.
    faiss.normalize_L2(
        embeddings
    )

    embedding_dimension = (
        embeddings.shape[1]
    )

    semantic_index = (
        faiss.IndexFlatIP(
            embedding_dimension
        )
    )

    semantic_index.add(
        embeddings
    )

    # =====================================================
    # BM25 INDEX
    # =====================================================

    tokenized_chunks = [
        tokenize_text(
            chunk_text
        )
        for chunk_text
        in chunk_texts
    ]

    bm25_index = BM25Okapi(
        tokenized_chunks
    )

    # =====================================================
    # HYBRID INDEX
    # =====================================================

    hybrid_index = {
        "semantic_index": (
            semantic_index
        ),

        "bm25_index": (
            bm25_index
        ),
    }

    return (
        chunks,
        hybrid_index,
    )


# =========================================================
# SEMANTIC SCORES
# =========================================================

def get_semantic_scores(
    query: str,
    chunks: list[dict[str, Any]],
    semantic_index,
) -> np.ndarray:
    """
    Calculate semantic similarity score
    for every chunk.
    """

    number_of_chunks = len(
        chunks
    )

    scores = np.zeros(
        number_of_chunks,
        dtype=np.float32,
    )

    if (
        number_of_chunks == 0
        or semantic_index is None
    ):
        return scores

    model = get_embedding_model()

    query_embedding = model.encode(
        [
            query
        ],
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype=np.float32,
    )

    faiss.normalize_L2(
        query_embedding
    )

    search_scores, search_indices = (
        semantic_index.search(
            query_embedding,
            number_of_chunks,
        )
    )

    for (
        similarity,
        chunk_index,
    ) in zip(
        search_scores[0],
        search_indices[0],
    ):

        if (
            chunk_index < 0
            or chunk_index
            >= number_of_chunks
        ):
            continue

        scores[
            chunk_index
        ] = float(
            similarity
        )

    return scores


# =========================================================
# BM25 SCORES
# =========================================================

def get_bm25_scores(
    query: str,
    bm25_index,
    number_of_chunks: int,
) -> np.ndarray:
    """
    Calculate lexical BM25 scores.
    """

    if (
        bm25_index is None
        or number_of_chunks <= 0
    ):
        return np.zeros(
            number_of_chunks,
            dtype=np.float32,
        )

    query_tokens = tokenize_text(
        query
    )

    if not query_tokens:
        return np.zeros(
            number_of_chunks,
            dtype=np.float32,
        )

    scores = bm25_index.get_scores(
        query_tokens
    )

    return np.asarray(
        scores,
        dtype=np.float32,
    )


# =========================================================
# HYBRID SEARCH
# =========================================================

def search_evidence(
    query: str,
    chunks: list[dict[str, Any]],
    index,
    top_k: int = 5,
    semantic_weight: float = SEMANTIC_WEIGHT,
    bm25_weight: float = BM25_WEIGHT,
) -> list[dict[str, Any]]:
    """
    Hybrid retrieval:

    final score =
        semantic score * semantic weight
        +
        BM25 score * BM25 weight
    """

    query = clean_text(
        query
    )

    if not query:
        return []

    if not chunks:
        return []

    if index is None:
        return []

    semantic_index = index.get(
        "semantic_index"
    )

    bm25_index = index.get(
        "bm25_index"
    )

    number_of_chunks = len(
        chunks
    )

    # =====================================================
    # SEMANTIC SEARCH
    # =====================================================

    semantic_scores = (
        get_semantic_scores(
            query=query,
            chunks=chunks,
            semantic_index=semantic_index,
        )
    )

    # =====================================================
    # BM25 SEARCH
    # =====================================================

    bm25_scores = get_bm25_scores(
        query=query,
        bm25_index=bm25_index,
        number_of_chunks=(
            number_of_chunks
        ),
    )

    # =====================================================
    # NORMALIZE SCORES
    # =====================================================

    normalized_semantic = (
        normalize_scores(
            semantic_scores
        )
    )

    normalized_bm25 = (
        normalize_scores(
            bm25_scores
        )
    )

    semantic_weight = max(
        0.0,
        float(
            semantic_weight
        ),
    )

    bm25_weight = max(
        0.0,
        float(
            bm25_weight
        ),
    )

    total_weight = (
        semantic_weight
        + bm25_weight
    )

    if total_weight <= 0:
        semantic_weight = 0.65
        bm25_weight = 0.35

    else:
        semantic_weight = (
            semantic_weight
            / total_weight
        )

        bm25_weight = (
            bm25_weight
            / total_weight
        )

    # =====================================================
    # FUSION
    # =====================================================

    hybrid_scores = (
        normalized_semantic
        * semantic_weight
        +
        normalized_bm25
        * bm25_weight
    )

    ranked_indices = np.argsort(
        hybrid_scores
    )[::-1]

    safe_top_k = max(
        1,
        min(
            int(top_k),
            number_of_chunks,
        ),
    )

    results = []

    for rank, chunk_index in enumerate(
        ranked_indices[
            :safe_top_k
        ],
        start=1,
    ):

        chunk = chunks[
            int(chunk_index)
        ]

        semantic_score = float(
            normalized_semantic[
                chunk_index
            ]
        )

        lexical_score = float(
            normalized_bm25[
                chunk_index
            ]
        )

        hybrid_score = float(
            hybrid_scores[
                chunk_index
            ]
        )

        results.append(
            {
                "text": chunk.get(
                    "text",
                    "",
                ),

                "document": (
                    chunk.get(
                        "document",
                        "Unknown Document",
                    )
                ),

                "page": chunk.get(
                    "page"
                ),

                "chunk_number": (
                    chunk.get(
                        "chunk_number"
                    )
                ),

                # Existing compatibility
                "similarity": round(
                    hybrid_score,
                    4,
                ),

                # New advanced scores
                "semantic_score": round(
                    semantic_score,
                    4,
                ),

                "bm25_score": round(
                    lexical_score,
                    4,
                ),

                "hybrid_score": round(
                    hybrid_score,
                    4,
                ),

                "retrieval_rank": (
                    rank
                ),

                "retrieval_method": (
                    "hybrid"
                ),

                "source_type": (
                    "pdf"
                ),

                "source_name": (
                    chunk.get(
                        "document",
                        "Unknown Document",
                    )
                ),
            }
        )

    return results