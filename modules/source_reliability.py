from urllib.parse import urlparse


TRUSTED_DOMAINS = {
    "who.int": 95,
    "nasa.gov": 98,
    "isro.gov.in": 98,
    "rbi.org.in": 96,
    "gov.in": 95,
    "nic.in": 95,
    "edu": 90,
    "ac.in": 90,
    "ieee.org": 95,
    "springer.com": 92,
    "sciencedirect.com": 92,
    "nature.com": 94,
    "nih.gov": 96,
    "pubmed.ncbi.nlm.nih.gov": 96,
    "un.org": 94,
    "worldbank.org": 93,
    "imf.org": 93,
    "wikipedia.org": 75,
}


def normalize_domain(url):
    if not url:
        return ""

    try:
        parsed = urlparse(url)

        domain = parsed.netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return ""


def get_source_reliability(url):
    """
    Returns reliability score between 0 and 100.
    """

    domain = normalize_domain(url)

    if not domain:
        return 50.0

    # Exact domain match
    for trusted_domain, score in TRUSTED_DOMAINS.items():

        if domain == trusted_domain:
            return float(score)

        if domain.endswith("." + trusted_domain):
            return float(score)

    # Government domains
    if domain.endswith(".gov"):
        return 95.0

    if domain.endswith(".gov.in"):
        return 95.0

    # Educational domains
    if domain.endswith(".edu"):
        return 90.0

    if domain.endswith(".edu.in"):
        return 90.0

    if domain.endswith(".ac.in"):
        return 90.0

    # Unknown source
    return 50.0


def get_source_category(score):
    if score >= 90:
        return "Highly Trusted"

    if score >= 75:
        return "Trusted"

    if score >= 60:
        return "Moderate"

    return "Low Confidence"


def analyze_source(url):
    score = get_source_reliability(url)

    category = get_source_category(score)

    return {
        "url": url,
        "domain": normalize_domain(url),
        "reliability_score": score,
        "category": category,
    }


def calculate_average_source_reliability(urls):
    if not urls:
        return 50.0

    scores = []

    for url in urls:
        scores.append(get_source_reliability(url))

    return sum(scores) / len(scores)


def get_source_badge(score):
    if score >= 90:
        return "🟢 Highly Trusted"

    if score >= 75:
        return "🔵 Trusted"

    if score >= 60:
        return "🟡 Moderate"

    return "🔴 Low Confidence"