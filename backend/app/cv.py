import io
from pathlib import Path

import pdfplumber
from docx import Document
from fastapi import HTTPException

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="CV is larger than 5 MB")
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif suffix == ".docx":
        text = "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    else:
        raise HTTPException(status_code=400, detail="Upload a PDF or DOCX file")
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text found in the CV; scanned images are not supported")
    return text
