from functools import lru_cache
from typing import Any
import re

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load the embedding model only once.
    """

    return SentenceTransformer(MODEL_NAME)


def clean_text(text: str) -> str:
    """
    Remove unnecessary spaces and line breaks.
    """

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def split_page_into_chunks(
    page_record: dict,
    chunk_size: int = 700,
    overlap: int = 150,
) -> list[dict]:
    """
    Split one PDF page into overlapping chunks while
    preserving source document and page number.
    """

    if overlap >= chunk_size:
        raise ValueError(
            "Overlap must be smaller than chunk size."
        )

    page_text = clean_text(
        page_record.get("text", "")
    )

    if not page_text:
        return []

    document_name = page_record.get(
        "document",
        "Unknown document",
    )

    page_number = page_record.get(
        "page",
        0,
    )

    chunks = []
    start = 0
    text_length = len(page_text)
    chunk_number = 1

    while start < text_length:
        end = min(
            start + chunk_size,
            text_length,
        )

        chunk_text = page_text[start:end].strip()

        if chunk_text:
            chunks.append(
                {
                    "text": chunk_text,
                    "document": document_name,
                    "page": page_number,
                    "chunk_number": chunk_number,
                }
            )

            chunk_number += 1

        if end >= text_length:
            break

        start = end - overlap

    return chunks


def create_document_chunks(
    page_records: list[dict],
) -> list[dict]:
    """
    Convert every PDF page into searchable chunks.
    """

    if not page_records:
        raise ValueError(
            "No PDF page records were supplied."
        )

    all_chunks = []

    for page_record in page_records:
        page_chunks = split_page_into_chunks(
            page_record
        )

        all_chunks.extend(page_chunks)

    return all_chunks


def build_evidence_index(
    page_records: list[dict],
) -> tuple[list[dict], Any]:
    """
    Create embeddings and a FAISS index for all PDF chunks.
    """

    chunks = create_document_chunks(
        page_records
    )

    if not chunks:
        raise ValueError(
            "No searchable document chunks were created."
        )

    model = get_embedding_model()

    chunk_texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = model.encode(
        chunk_texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    embedding_dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(
        embedding_dimension
    )

    index.add(embeddings)

    return chunks, index


def search_evidence(
    claim: str,
    chunks: list[dict],
    index: Any,
    top_k: int = 5,
) -> list[dict]:
    """
    Find relevant PDF evidence for one factual claim.
    """

    clean_claim = claim.strip()

    if not clean_claim:
        raise ValueError(
            "Claim cannot be empty."
        )

    if not chunks:
        raise ValueError(
            "Document chunks are missing."
        )

    model = get_embedding_model()

    claim_embedding = model.encode(
        [clean_claim],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    claim_embedding = np.asarray(
        claim_embedding,
        dtype=np.float32,
    )

    result_count = min(
        top_k,
        len(chunks),
    )

    similarity_scores, chunk_indexes = index.search(
        claim_embedding,
        result_count,
    )

    results = []

    for score, chunk_index in zip(
        similarity_scores[0],
        chunk_indexes[0],
    ):
        if chunk_index < 0:
            continue

        selected_chunk = chunks[
            int(chunk_index)
        ]

        results.append(
            {
                "text": selected_chunk["text"],
                "similarity": round(
                    float(score),
                    4,
                ),
                "document": selected_chunk[
                    "document"
                ],
                "page": selected_chunk["page"],
                "chunk_number": selected_chunk[
                    "chunk_number"
                ],
            }
        )

    return results