def calculate_overall_score(
    verification_results: list[dict]
) -> int:
    """
    Calculate the average confidence score of all claims.
    """

    if not verification_results:
        return 0

    scores = []

    for result in verification_results:
        score = result.get("confidence_score", 0)

        try:
            score = int(score)
        except (TypeError, ValueError):
            score = 0

        score = max(0, min(100, score))
        scores.append(score)

    return round(sum(scores) / len(scores))


def count_statuses(
    verification_results: list[dict]
) -> dict:
    """
    Count claims according to their verification status.
    """

    counts = {
        "Verified": 0,
        "Partially Verified": 0,
        "Unsupported": 0,
        "Incorrect": 0
    }

    for result in verification_results:
        status = result.get("status")

        if status in counts:
            counts[status] += 1

    return counts


def get_trust_level(score: int) -> str:
    """
    Convert numerical score into a readable trust level.
    """

    if score >= 80:
        return "High Trust"

    if score >= 50:
        return "Medium Trust"

    return "Low Trust"