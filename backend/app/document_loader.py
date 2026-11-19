from pathlib import Path
import fitz
from docx import Document

def extract_text(path):
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        doc = fitz.open(p)
        return "\n".join(page.get_text() for page in doc)
    if p.suffix.lower() == ".docx":
        doc = Document(p)
        return "\n".join(x.text for x in doc.paragraphs if x.text.strip())
    if p.suffix.lower() == ".txt":
        return p.read_text(encoding="utf-8", errors="ignore")
    raise ValueError("Upload PDF, DOCX or TXT only.")
