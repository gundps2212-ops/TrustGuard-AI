import json
from datetime import datetime
from typing import Any


def build_final_response(
    verification_results: list[dict[str, Any]]
) -> str:
    """
    Build a trusted response using only verified and
    partially verified claims.
    """

    verified_claims = []
    partial_claims = []
    flagged_claims = []

    for result in verification_results:
        claim = result.get("claim", "").strip()
        status = result.get("status", "Unsupported")

        if not claim:
            continue

        if status == "Verified":
            verified_claims.append(claim)

        elif status == "Partially Verified":
            partial_claims.append(claim)

        else:
            flagged_claims.append(
                {
                    "claim": claim,
                    "status": status
                }
            )

    response_parts = []

    if verified_claims:
        response_parts.append("Verified information:")

        for claim in verified_claims:
            response_parts.append(f"• {claim}")

    if partial_claims:
        response_parts.append(
            "\nInformation that is only partially supported:"
        )

        for claim in partial_claims:
            response_parts.append(f"• {claim}")

    if flagged_claims:
        response_parts.append(
            "\nStatements excluded from the trusted response:"
        )

        for item in flagged_claims:
            response_parts.append(
                f"• [{item['status']}] {item['claim']}"
            )

    if not verified_claims and not partial_claims:
        return (
            "No claims from the AI-generated answer could be "
            "reliably verified using the uploaded document."
        )

    return "\n".join(response_parts)


def create_report_data(
    question: str,
    document_name: str,
    ai_answer: str,
    overall_score: int,
    trust_level: str,
    verification_results: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Create complete verification report data.
    """

    return {
        "project": "TrustGuard AI",
        "report_generated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
        "document_name": document_name,
        "question": question,
        "original_ai_answer": ai_answer,
        "overall_trust_score": overall_score,
        "trust_level": trust_level,
        "final_verified_response": build_final_response(
            verification_results
        ),
        "claim_results": verification_results
    }


def create_json_report(
    report_data: dict[str, Any]
) -> str:
    """
    Convert report into formatted JSON.
    """

    return json.dumps(
        report_data,
        indent=4,
        ensure_ascii=False
    )


def create_text_report(
    report_data: dict[str, Any]
) -> str:
    """
    Convert report into readable text format.
    """

    lines = [
        "=" * 65,
        "TRUSTGUARD AI – FACT VERIFICATION REPORT",
        "=" * 65,
        "",
        f"Generated At: {report_data['report_generated_at']}",
        f"Document: {report_data['document_name']}",
        f"Question: {report_data['question']}",
        "",
        "ORIGINAL AI ANSWER",
        "-" * 65,
        report_data["original_ai_answer"],
        "",
        "VERIFICATION SUMMARY",
        "-" * 65,
        (
            f"Overall Trust Score: "
            f"{report_data['overall_trust_score']}%"
        ),
        f"Trust Level: {report_data['trust_level']}",
        "",
        "FINAL VERIFIED RESPONSE",
        "-" * 65,
        report_data["final_verified_response"],
        "",
        "INDIVIDUAL CLAIM RESULTS",
        "-" * 65
    ]

    for number, result in enumerate(
        report_data["claim_results"],
        start=1
    ):
        lines.extend(
            [
                "",
                f"Claim {number}: {result.get('claim', '')}",
                f"Status: {result.get('status', '')}",
                (
                    "Confidence Score: "
                    f"{result.get('confidence_score', 0)}%"
                ),
                (
                    "Explanation: "
                    f"{result.get('explanation', '')}"
                ),
                (
                    "Supporting Evidence: "
                    f"{result.get('supporting_evidence', '')}"
                ),
                "-" * 65
            ]
        )

    lines.extend(
        [
            "",
            (
                "Note: Results are based only on the evidence "
                "available in the uploaded document."
            )
        ]
    )

    return "\n".join(lines)