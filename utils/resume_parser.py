from __future__ import annotations

from io import BytesIO

import pdfplumber
from pypdf import PdfReader


class ResumeParserError(Exception):
    pass


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_chunks: list[str] = []

    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ''
                if text.strip():
                    text_chunks.append(text)
    except Exception:
        text_chunks = []

    if not text_chunks:
        try:
            reader = PdfReader(BytesIO(file_bytes))
            for page in reader.pages:
                text = page.extract_text() or ''
                if text.strip():
                    text_chunks.append(text)
        except Exception as exc:
            raise ResumeParserError(f'Unable to read resume PDF: {exc}') from exc

    extracted = '\n'.join(text_chunks).strip()
    if not extracted:
        raise ResumeParserError('The uploaded PDF did not contain readable text.')
    return extracted
