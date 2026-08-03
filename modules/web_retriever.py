import os
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from tavily import TavilyClient


load_dotenv()


TRUSTED_DOMAIN_GROUPS = {
    "No domain filter": [],
    "Indian Government": [
        "india.gov.in",
        "gov.in",
        "nic.in",
    ],
    "Legal": [
        "sci.gov.in",
        "legislative.gov.in",
        "doj.gov.in",
        "lawmin.gov.in",
    ],
    "Banking and Finance": [
        "rbi.org.in",
        "sebi.gov.in",
        "finmin.gov.in",
        "irdai.gov.in",
    ],
    "Healthcare": [
        "who.int",
        "cdc.gov",
        "nih.gov",
        "mohfw.gov.in",
    ],
    "Education and Research": [
        "education.gov.in",
        "ugc.gov.in",
        "aicte-india.org",
        "ncert.nic.in",
    ],
}


def get_tavily_client() -> TavilyClient:
    """
    Create and return a Tavily client.
    """

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY was not found in the .env file."
        )

    return TavilyClient(api_key=api_key)


def get_domain_from_url(url: str) -> str:
    """
    Extract domain name from a URL.
    """

    try:
        domain = urlparse(url).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return "Unknown domain"


def get_relevance_level(score: float) -> str:
    """
    Convert Tavily relevance score into a readable label.

    This represents search relevance, not factual correctness.
    """

    if score >= 0.75:
        return "High relevance"

    if score >= 0.50:
        return "Medium relevance"

    return "Low relevance"


def search_web_evidence(
    claim: str,
    max_results: int = 3,
    domain_group: str = "No domain filter",
    minimum_score: float = 0.50,
) -> list[dict[str, Any]]:
    """
    Search web evidence for one factual claim.

    Args:
        claim:
            Factual claim to search.

        max_results:
            Maximum search results.

        domain_group:
            Preferred trusted-domain category.

        minimum_score:
            Minimum Tavily relevance score.

    Returns:
        Web evidence records compatible with TrustGuard AI.
    """

    clean_claim = claim.strip()

    if not clean_claim:
        raise ValueError("Claim cannot be empty.")

    max_results = max(
        1,
        min(max_results, 10),
    )

    minimum_score = max(
        0.0,
        min(float(minimum_score), 1.0),
    )

    selected_domains = TRUSTED_DOMAIN_GROUPS.get(
        domain_group,
        [],
    )

    client = get_tavily_client()

    search_arguments = {
        "query": clean_claim,
        "search_depth": "basic",
        "topic": "general",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
    }

    if selected_domains:
        search_arguments["include_domains"] = selected_domains

    try:
        response = client.search(
            **search_arguments
        )

        web_results = []

        for item in response.get("results", []):
            content = (
                item.get("content") or ""
            ).strip()

            if not content:
                continue

            try:
                score = float(
                    item.get("score", 0)
                )
            except (TypeError, ValueError):
                score = 0.0

            # Ignore low-relevance results
            if score < minimum_score:
                continue

            title = (
                item.get("title")
                or "Unknown web source"
            )

            source_url = (
                item.get("url") or ""
            )

            domain = get_domain_from_url(
                source_url
            )

            web_results.append(
                {
                    "text": content,
                    "similarity": round(score, 4),
                    "document": title,
                    "page": "Web",
                    "chunk_number": "Web",
                    "url": source_url,
                    "domain": domain,
                    "source_type": "web",
                    "domain_group": domain_group,
                    "relevance_level": get_relevance_level(
                        score
                    ),
                }
            )

        return web_results

    except Exception as error:
        raise RuntimeError(
            f"Web evidence search failed: {error}"
        ) from error