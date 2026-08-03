from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PAGE_WIDTH, PAGE_HEIGHT = A4


def clean_pdf_text(value: Any) -> str:
    """
    Convert a value into safe ReportLab paragraph text.

    It also replaces some Unicode symbols that may not render
    correctly with the built-in Helvetica font.
    """

    if value is None:
        return ""

    text = str(value)

    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u2192": "->",
        "\u00a0": " ",
    }

    for old_character, new_character in replacements.items():
        text = text.replace(
            old_character,
            new_character,
        )

    return escape(text).replace(
        "\n",
        "<br/>",
    )


def safe_integer(
    value: Any,
    default: int = 0,
) -> int:
    """
    Convert a value safely into an integer.
    """

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def create_styles() -> dict[str, ParagraphStyle]:
    """
    Create styles used inside the PDF report.
    """

    sample_styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            name="TrustGuardTitle",
            parent=sample_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324D"),
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            name="TrustGuardSubtitle",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=18,
        ),
        "heading1": ParagraphStyle(
            name="TrustGuardHeading1",
            parent=sample_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#17324D"),
            spaceBefore=10,
            spaceAfter=8,
        ),
        "heading2": ParagraphStyle(
            name="TrustGuardHeading2",
            parent=sample_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1F4E78"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "normal": ParagraphStyle(
            name="TrustGuardNormal",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            name="TrustGuardSmall",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=4,
        ),
        "claim": ParagraphStyle(
            name="TrustGuardClaim",
            parent=sample_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#111827"),
            spaceAfter=6,
        ),
        "footer": ParagraphStyle(
            name="TrustGuardFooter",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#6B7280"),
        ),
    }


def status_background(status: str):
    """
    Return a background colour for a verification status.
    """

    status_colours = {
        "Verified": colors.HexColor("#DCFCE7"),
        "Partially Verified": colors.HexColor("#FEF3C7"),
        "Unsupported": colors.HexColor("#DBEAFE"),
        "Incorrect": colors.HexColor("#FEE2E2"),
    }

    return status_colours.get(
        status,
        colors.HexColor("#F3F4F6"),
    )


def draw_header_footer(
    canvas: Canvas,
    document: SimpleDocTemplate,
) -> None:
    """
    Add header, footer and page number to every page.
    """

    canvas.saveState()

    canvas.setStrokeColor(
        colors.HexColor("#D1D5DB")
    )
    canvas.setLineWidth(0.5)

    canvas.line(
        18 * mm,
        PAGE_HEIGHT - 14 * mm,
        PAGE_WIDTH - 18 * mm,
        PAGE_HEIGHT - 14 * mm,
    )

    canvas.setFont(
        "Helvetica-Bold",
        8,
    )
    canvas.setFillColor(
        colors.HexColor("#17324D")
    )

    canvas.drawString(
        18 * mm,
        PAGE_HEIGHT - 11 * mm,
        "TrustGuard AI - Verification Report",
    )

    canvas.line(
        18 * mm,
        14 * mm,
        PAGE_WIDTH - 18 * mm,
        14 * mm,
    )

    canvas.setFont(
        "Helvetica",
        7.5,
    )
    canvas.setFillColor(
        colors.HexColor("#6B7280")
    )

    canvas.drawString(
        18 * mm,
        9 * mm,
        "Generated by TrustGuard AI",
    )

    canvas.drawRightString(
        PAGE_WIDTH - 18 * mm,
        9 * mm,
        f"Page {document.page}",
    )

    canvas.restoreState()


def create_summary_table(
    report_data: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> Table:
    """
    Create the main verification summary table.
    """

    claim_results = report_data.get(
        "claim_results",
        [],
    )

    status_counts = {
        "Verified": 0,
        "Partially Verified": 0,
        "Unsupported": 0,
        "Incorrect": 0,
    }

    for result in claim_results:
        status = result.get(
            "status",
            "Unsupported",
        )

        if status in status_counts:
            status_counts[status] += 1

    table_data = [
        [
            Paragraph(
                "<b>Overall Trust Score</b>",
                styles["normal"],
            ),
            Paragraph(
                f"{safe_integer(report_data.get('overall_trust_score'))}%",
                styles["normal"],
            ),
        ],
        [
            Paragraph(
                "<b>Trust Level</b>",
                styles["normal"],
            ),
            Paragraph(
                clean_pdf_text(
                    report_data.get(
                        "trust_level",
                        "Unknown",
                    )
                ),
                styles["normal"],
            ),
        ],
        [
            Paragraph(
                "<b>Total Claims</b>",
                styles["normal"],
            ),
            Paragraph(
                str(len(claim_results)),
                styles["normal"],
            ),
        ],
        [
            Paragraph(
                "<b>Verified</b>",
                styles["normal"],
            ),
            Paragraph(
                str(status_counts["Verified"]),
                styles["normal"],
            ),
        ],
        [
            Paragraph(
                "<b>Partially Verified</b>",
                styles["normal"],
            ),
            Paragraph(
                str(
                    status_counts[
                        "Partially Verified"
                    ]
                ),
                styles["normal"],
            ),
        ],
        [
            Paragraph(
                "<b>Unsupported</b>",
                styles["normal"],
            ),
            Paragraph(
                str(status_counts["Unsupported"]),
                styles["normal"],
            ),
        ],
        [
            Paragraph(
                "<b>Incorrect</b>",
                styles["normal"],
            ),
            Paragraph(
                str(status_counts["Incorrect"]),
                styles["normal"],
            ),
        ],
    ]

    table = Table(
        table_data,
        colWidths=[
            65 * mm,
            105 * mm,
        ],
        repeatRows=0,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#E8EEF5"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    return table


def create_evidence_source_text(
    evidence: dict[str, Any],
) -> str:
    """
    Create a readable PDF or web evidence source label.
    """

    source_type = evidence.get(
        "source_type",
        "pdf",
    )

    document_name = evidence.get(
        "document",
        "Unknown source",
    )

    if source_type == "web":
        domain = evidence.get(
            "domain",
            "",
        )

        url = evidence.get(
            "url",
            "",
        )

        source_text = (
            f"Web source: {document_name}"
        )

        if domain:
            source_text += f" ({domain})"

        if url:
            source_text += f"<br/>URL: {url}"

        return clean_pdf_text(source_text)

    page_number = evidence.get(
        "page",
        "Unknown",
    )

    return clean_pdf_text(
        f"PDF source: {document_name}, "
        f"Page: {page_number}"
    )


def create_claim_section(
    claim_number: int,
    result: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> list:
    """
    Create flowables for one claim result.
    """

    status = result.get(
        "status",
        "Unsupported",
    )

    confidence_score = safe_integer(
        result.get(
            "confidence_score",
            0,
        )
    )

    claim_text = clean_pdf_text(
        result.get(
            "claim",
            "Claim unavailable.",
        )
    )

    explanation = clean_pdf_text(
        result.get(
            "explanation",
            "Explanation unavailable.",
        )
    )

    selected_evidence = clean_pdf_text(
        result.get(
            "supporting_evidence",
            "",
        )
        or "No supporting evidence was selected."
    )

    status_table = Table(
        [
            [
                Paragraph(
                    f"<b>Status:</b> {clean_pdf_text(status)}",
                    styles["normal"],
                ),
                Paragraph(
                    (
                        "<b>Confidence Score:</b> "
                        f"{confidence_score}%"
                    ),
                    styles["normal"],
                ),
            ]
        ],
        colWidths=[
            85 * mm,
            85 * mm,
        ],
    )

    status_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    status_background(status),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.HexColor("#9CA3AF"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    section = [
        Paragraph(
            f"Claim {claim_number}",
            styles["heading2"],
        ),
        Paragraph(
            claim_text,
            styles["claim"],
        ),
        status_table,
        Spacer(
            1,
            3 * mm,
        ),
        Paragraph(
            "<b>Explanation</b>",
            styles["normal"],
        ),
        Paragraph(
            explanation,
            styles["normal"],
        ),
        Paragraph(
            "<b>Selected Supporting Evidence</b>",
            styles["normal"],
        ),
        Paragraph(
            selected_evidence,
            styles["normal"],
        ),
    ]

    evidence_items = result.get(
        "evidence",
        [],
    )

    if evidence_items:
        section.append(
            Paragraph(
                "<b>Retrieved Evidence Sources</b>",
                styles["normal"],
            )
        )

        for evidence_number, evidence in enumerate(
            evidence_items[:5],
            start=1,
        ):
            source_label = (
                create_evidence_source_text(
                    evidence
                )
            )

            evidence_text = clean_pdf_text(
                evidence.get(
                    "text",
                    "Evidence text unavailable.",
                )
            )

            similarity = evidence.get(
                "similarity",
                0,
            )

            try:
                similarity_text = (
                    f"{float(similarity):.4f}"
                )
            except (TypeError, ValueError):
                similarity_text = "0.0000"

            evidence_data = [
                [
                    Paragraph(
                        (
                            f"<b>Evidence {evidence_number}</b>"
                            f"<br/>{source_label}"
                            f"<br/><b>Relevance:</b> "
                            f"{similarity_text}"
                        ),
                        styles["small"],
                    )
                ],
                [
                    Paragraph(
                        evidence_text,
                        styles["small"],
                    )
                ],
            ]

            evidence_table = Table(
                evidence_data,
                colWidths=[
                    170 * mm,
                ],
            )

            evidence_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#F1F5F9"),
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.4,
                            colors.HexColor("#CBD5E1"),
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            6,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            6,
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            5,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            5,
                        ),
                    ]
                )
            )

            section.extend(
                [
                    evidence_table,
                    Spacer(
                        1,
                        2 * mm,
                    ),
                ]
            )

    section.extend(
        [
            Spacer(
                1,
                3 * mm,
            ),
        ]
    )

    return section


def create_pdf_report(
    report_data: dict[str, Any],
) -> bytes:
    """
    Generate and return a professional PDF verification report.

    Args:
        report_data:
            Dictionary generated by create_report_data().

    Returns:
        PDF file content as bytes.
    """

    if not isinstance(report_data, dict):
        raise TypeError(
            "report_data must be a dictionary."
        )

    output_buffer = BytesIO()

    document = SimpleDocTemplate(
        output_buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="TrustGuard AI Verification Report",
        author="TrustGuard AI",
        subject=(
            "Hallucination Detection and "
            "Fact Verification Report"
        ),
    )

    styles = create_styles()
    story = []

    # -----------------------------------------------------
    # REPORT TITLE
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "TrustGuard AI",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "Hallucination Detection and Fact Verification Report",
            styles["subtitle"],
        )
    )

    generated_time = report_data.get(
        "report_generated_at",
        datetime.now().isoformat(
            timespec="seconds"
        ),
    )

    selected_model = report_data.get(
        "selected_llm",
        "Gemini",
    )

    report_information = [
        [
            Paragraph(
                "<b>Generated At</b>",
                styles["normal"],
            ),
            Paragraph(
                clean_pdf_text(generated_time),
                styles["normal"],
            ),
        ],
        [
            Paragraph(
                "<b>Selected AI Model</b>",
                styles["normal"],
            ),
            Paragraph(
                clean_pdf_text(selected_model),
                styles["normal"],
            ),
        ],
        [
            Paragraph(
                "<b>Document(s)</b>",
                styles["normal"],
            ),
            Paragraph(
                clean_pdf_text(
                    report_data.get(
                        "document_name",
                        "Not available",
                    )
                ),
                styles["normal"],
            ),
        ],
    ]

    information_table = Table(
        report_information,
        colWidths=[
            45 * mm,
            125 * mm,
        ],
    )

    information_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#E8EEF5"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.extend(
        [
            information_table,
            Spacer(
                1,
                5 * mm,
            ),
        ]
    )

    # -----------------------------------------------------
    # QUESTION
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "User Question",
            styles["heading1"],
        )
    )

    story.append(
        Paragraph(
            clean_pdf_text(
                report_data.get(
                    "question",
                    "Question unavailable.",
                )
            ),
            styles["normal"],
        )
    )

    # -----------------------------------------------------
    # ORIGINAL ANSWER
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Original AI Answer",
            styles["heading1"],
        )
    )

    story.append(
        Paragraph(
            clean_pdf_text(
                report_data.get(
                    "original_ai_answer",
                    "AI answer unavailable.",
                )
            ),
            styles["normal"],
        )
    )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Verification Summary",
            styles["heading1"],
        )
    )

    story.append(
        create_summary_table(
            report_data,
            styles,
        )
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    # -----------------------------------------------------
    # FINAL VERIFIED RESPONSE
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Final Verified Response",
            styles["heading1"],
        )
    )

    story.append(
        Paragraph(
            clean_pdf_text(
                report_data.get(
                    "final_verified_response",
                    "Verified response unavailable.",
                )
            ),
            styles["normal"],
        )
    )

    story.append(
        PageBreak()
    )

    # -----------------------------------------------------
    # CLAIM RESULTS
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Individual Claim Verification Results",
            styles["heading1"],
        )
    )

    claim_results = report_data.get(
        "claim_results",
        [],
    )

    if not claim_results:
        story.append(
            Paragraph(
                "No claim verification results are available.",
                styles["normal"],
            )
        )

    for claim_number, result in enumerate(
        claim_results,
        start=1,
    ):
        story.extend(
            create_claim_section(
                claim_number,
                result,
                styles,
            )
        )

    # -----------------------------------------------------
    # DISCLAIMER
    # -----------------------------------------------------

    story.extend(
        [
            Spacer(
                1,
                5 * mm,
            ),
            Paragraph(
                "Important Note",
                styles["heading1"],
            ),
            Paragraph(
                (
                    "This report is based on evidence retrieved "
                    "from uploaded PDF documents and optional web "
                    "sources. A relevance score measures similarity "
                    "to a claim and does not by itself guarantee "
                    "factual correctness."
                ),
                styles["small"],
            ),
        ]
    )

    document.build(
        story,
        onFirstPage=draw_header_footer,
        onLaterPages=draw_header_footer,
    )

    pdf_bytes = output_buffer.getvalue()
    output_buffer.close()

    return pdf_bytes