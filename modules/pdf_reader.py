from typing import BinaryIO

from pypdf import PdfReader


def extract_pdf_pages(
    pdf_file: BinaryIO,
    document_name: str | None = None,
) -> tuple[list[dict], int]:
    """
    Extract text page-by-page from one PDF.

    Returns:
        page_records:
            [
                {
                    "document": "example.pdf",
                    "page": 1,
                    "text": "Page text..."
                }
            ]

        page_count:
            Total pages in the PDF.
    """

    if pdf_file is None:
        raise ValueError("PDF file is required.")

    pdf_file.seek(0)

    reader = PdfReader(pdf_file)

    file_name = (
        document_name
        or getattr(pdf_file, "name", "uploaded_document.pdf")
    )

    page_records = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        page_text = page.extract_text() or ""

        page_text = page_text.strip()

        if page_text:
            page_records.append(
                {
                    "document": file_name,
                    "page": page_number,
                    "text": page_text,
                }
            )

    return page_records, len(reader.pages)


def extract_multiple_pdfs(
    uploaded_files: list,
) -> tuple[list[dict], int]:
    """
    Extract text from multiple PDF files while preserving
    document names and page numbers.
    """

    if not uploaded_files:
        raise ValueError(
            "At least one PDF document is required."
        )

    all_page_records = []
    total_page_count = 0

    for uploaded_file in uploaded_files:
        page_records, page_count = extract_pdf_pages(
            pdf_file=uploaded_file,
            document_name=uploaded_file.name,
        )

        all_page_records.extend(page_records)
        total_page_count += page_count

    return all_page_records, total_page_count


def extract_pdf_text(
    pdf_file: BinaryIO,
) -> tuple[str, int]:
    """
    Compatibility function for older code.
    """

    page_records, page_count = extract_pdf_pages(
        pdf_file
    )

    complete_text = "\n\n".join(
        (
            f"--- {record['document']} "
            f"| Page {record['page']} ---\n"
            f"{record['text']}"
        )
        for record in page_records
    )

    return complete_text, page_count