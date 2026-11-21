"""PyMuPDF text extraction, cleaning, and section header detection module (C-PROC).

Extracts text from PDF documents page-by-page, retaining page numbers, detecting
section headings, and cleaning extraction artifacts.
"""

import re
from typing import List, Optional
import fitz  # PyMuPDF
from pydantic import BaseModel, Field

from backend.app.core.errors import ValidationError
from backend.app.core.logging import logger

# Regex for common section heading formats in university documents:
# e.g., "1.1 Overview", "Section 2: Grading", "Chapter 4", "Article III"
SECTION_HEADER_PATTERN = re.compile(
    r"^(?:Section\s+\d+|Chapter\s+\d+|Article\s+[IVXLCDM]+|\d+\.\d+(?:\.\d+)?)\s*[:.-]?\s*(.+)$",
    re.IGNORECASE,
)

# Patterns for page footer/header artifacts (e.g. "Page 1 of 12", "Page 4", "- 5 -")
PAGE_ARTIFACT_PATTERN = re.compile(
    r"^(?:page\s+\d+(?:\s+of\s+\d+)?|-?\s*\d+\s*-?)$",
    re.IGNORECASE,
)


class ExtractedPage(BaseModel):
    """Container for page-level extracted text and metadata."""

    page_number: int = Field(..., description="1-indexed source PDF page number.")
    text: str = Field(..., description="Cleaned text content of the page.")
    section: Optional[str] = Field(default=None, description="Active section title on this page.")
    char_count: int = Field(..., description="Character length of cleaned text.")


def clean_text(raw_text: str) -> str:
    """Cleans unnecessary whitespace, non-printable characters, and extraction artifacts.

    - Replaces non-breaking and special unicode spaces with ASCII space.
    - Removes isolated page numbers or header/footer lines.
    - Normalizes multi-character whitespace while preserving paragraph breaks.
    - Collapses excessive newlines.
    """
    if not raw_text:
        return ""

    # Normalize unicode spaces
    cleaned = raw_text.replace("\xa0", " ").replace("\u200b", "")

    # Normalize carriage returns
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    lines = cleaned.split("\n")
    filtered_lines: List[str] = []

    for line in lines:
        trimmed = line.strip()
        # Drop lines that are solely page number artifacts
        if PAGE_ARTIFACT_PATTERN.match(trimmed):
            continue
        # Normalize internal whitespace within line
        trimmed = re.sub(r"[ \t]+", " ", trimmed)
        filtered_lines.append(trimmed)

    # Rejoin lines
    result = "\n".join(filtered_lines)

    # Collapse 3 or more newlines into 2 (clean paragraph break)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def detect_section_header(text: str) -> Optional[str]:
    """Inspects the first few non-empty lines of text for a section header."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines[:5]:
        match = SECTION_HEADER_PATTERN.match(line)
        if match:
            # Return detected heading
            return line[:100].strip()
        # Common uppercase standalone headings (e.g. "ACADEMIC REGULATIONS")
        if len(line) >= 4 and line.isupper() and not line.isdigit() and len(line) <= 60:
            return line[:100].strip()
    return None


def extract_text_from_pdf(pdf_bytes: bytes) -> List[ExtractedPage]:
    """Extracts text page-by-page from raw PDF bytes using PyMuPDF.

    Args:
        pdf_bytes: Raw bytes of the uploaded PDF file.

    Returns:
        List of ExtractedPage instances with cleaned text, page numbers, and detected sections.

    Raises:
        ValidationError: If the PDF is corrupted, password-protected, or contains no readable text.
    """
    if not pdf_bytes:
        raise ValidationError("Cannot extract text from empty PDF bytes.")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        logger.error("PyMuPDF failed to open PDF document: %s", exc)
        raise ValidationError(f"Invalid or corrupted PDF file: {exc}")

    if doc.is_encrypted:
        doc.close()
        raise ValidationError("Password-protected or encrypted PDFs are not supported.")

    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        raise ValidationError("PDF document contains 0 pages.")

    extracted_pages: List[ExtractedPage] = []
    current_section: Optional[str] = None
    total_extracted_chars = 0

    for page_idx in range(total_pages):
        page = doc[page_idx]
        raw_text = page.get_text("text")
        page_num = page_idx + 1

        cleaned = clean_text(raw_text)

        # Check for section header on this page
        detected_section = detect_section_header(cleaned)
        if detected_section:
            current_section = detected_section

        if cleaned:
            total_extracted_chars += len(cleaned)
            extracted_pages.append(
                ExtractedPage(
                    page_number=page_num,
                    text=cleaned,
                    section=current_section,
                    char_count=len(cleaned),
                )
            )

    doc.close()

    if total_extracted_chars == 0:
        logger.warning("PDF extraction returned 0 characters of text across %d pages.", total_pages)
        raise ValidationError(
            "No extractable text found in PDF. Scanned image-only PDFs without OCR are not supported."
        )

    logger.info(
        "Extracted %d characters from %d non-empty pages (out of %d total pages).",
        total_extracted_chars,
        len(extracted_pages),
        total_pages,
    )
    return extracted_pages
