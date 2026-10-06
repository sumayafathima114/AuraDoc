import hashlib
import io
import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

SECTION_PATTERN = re.compile(
    r"^\s*(?:(?:section|article|clause)\s+|§\s*)([\w.-]+)(?:\s*[:.\-–]\s*(.*))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedPDF:
    data: bytes
    sha256_hash: str
    page_count: int
    sections: list[dict[str, Any]]
    filename: str


async def read_and_parse_pdf(file: UploadFile, max_bytes: int) -> ParsedPDF:
    filename = (file.filename or "contract.pdf").replace("\\", "/").split("/")[-1].strip()
    if not filename or len(filename) > 255 or not filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Upload a PDF document with a .pdf filename.")
    chunks: list[bytes] = []
    total = 0
    while part := await file.read(1024 * 1024):
        total += len(part)
        if total > max_bytes:
            raise HTTPException(413, "The uploaded document exceeds the configured size limit.")
        chunks.append(part)
    data = b"".join(chunks)
    if not data.startswith(b"%PDF-"):
        raise HTTPException(415, "The uploaded file is not a valid PDF document.")
    try:
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise HTTPException(422, "Encrypted PDFs are not supported for MVP processing.")
        page_texts = [page.extract_text() or "" for page in reader.pages]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "The PDF could not be read safely.") from exc
    if not page_texts or not any(text.strip() for text in page_texts):
        raise HTTPException(422, "This PDF contains no extractable text; OCR is not enabled in the MVP.")

    sections: list[dict[str, Any]] = []
    for page_number, page_text in enumerate(page_texts, start=1):
        active_section: str | None = None
        active_clause: str | None = None
        paragraphs = re.split(r"\n\s*\n|(?<=\.)\s{2,}", page_text)
        paragraph_index = 0
        for paragraph in paragraphs:
            content = " ".join(line.strip() for line in paragraph.splitlines()).strip()
            if not content:
                continue
            heading = SECTION_PATTERN.match(content[:300])
            if heading:
                active_clause = heading.group(1)
                active_section = heading.group(2).strip() if heading.group(2) else active_section
            for offset in range(0, len(content), 1800):
                chunk = content[offset : offset + 1800].strip()
                if not chunk:
                    continue
                sections.append(
                    {
                        "page_number": page_number,
                        "section_label": active_section,
                        "clause_label": active_clause,
                        "paragraph_index": paragraph_index,
                        "content": chunk,
                        "content_hash": hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
                    }
                )
                paragraph_index += 1
    return ParsedPDF(
        data=data,
        sha256_hash=hashlib.sha256(data).hexdigest(),
        page_count=len(page_texts),
        sections=sections,
        filename=filename,
    )
