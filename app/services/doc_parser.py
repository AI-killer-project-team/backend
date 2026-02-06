from typing import Optional
from pypdf import PdfReader


def extract_text_from_pdf(file_obj) -> str:
    reader = PdfReader(file_obj)
    texts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            texts.append(text)
    return "\n".join(texts).strip()


def extract_text_from_upload(file_obj, filename: Optional[str]) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(file_obj)

    # fallback: try to read as text
    try:
        data = file_obj.read()
        if isinstance(data, bytes):
            return data.decode("utf-8", errors="ignore").strip()
        return str(data).strip()
    except Exception:
        return ""
