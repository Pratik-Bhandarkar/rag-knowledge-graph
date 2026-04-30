import fitz
import json
import re
from pathlib import Path

PAYSLIPS_FOLDER = Path(r"D:\Personal\Projects\rag-knowledge-graph\documents\payslips")
CHUNKS_FOLDER = Path(r"D:\Personal\Projects\rag-knowledge-graph\chunks")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

ABBREVIATIONS = {
    "HI": "Health Insurance (Krankenversicherung)",
    "PI": "Pension Insurance (Rentenversicherung)",
    "UI": "Unemployment Insurance (Arbeitslosenversicherung)",
    "CI": "Care Insurance (Pflegeversicherung)",
    "SI": "Social Insurance (Sozialversicherung)",
    "KV-Beitrag": "Health Insurance Contribution",
    "RV-Beitrag": "Pension Insurance Contribution",
    "AV-Beitrag": "Unemployment Insurance Contribution",
    "PV-Beitrag": "Care Insurance Contribution",
}

def expand_abbreviations(text):
    """Expands known abbreviations using regex word boundaries."""
    for abbr, full_form in ABBREVIATIONS.items():
        pattern = r'\b' + re.escape(abbr) + r'\b'
        text = re.sub(pattern, full_form, text)
    return text

def extract_text_from_pdf(pdf_path):
    """Extracts all text from a PDF."""
    document = fitz.open(pdf_path)
    full_text = ""
    for page in document:
        full_text += page.get_text()
    document.close()
    return full_text

def chunk_text(text, source_file):
    """Breaks text into overlapping chunks with metadata."""
    chunks = []
    start = 0
    chunk_number = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunk_content = text[start:end]

        chunk = {
            "chunk_number": chunk_number,
            "source_file": source_file,
            "content": chunk_content
        }

        chunks.append(chunk)
        chunk_number += 1
        start = end - CHUNK_OVERLAP

    return chunks

CHUNKS_FOLDER.mkdir(exist_ok=True)

for pdf_file in PAYSLIPS_FOLDER.glob("*.pdf"):
    print(f"Processing: {pdf_file.name}")
    
    text = extract_text_from_pdf(pdf_file)
    text = expand_abbreviations(text)
    chunks = chunk_text(text, source_file=pdf_file.name)

    output_file = CHUNKS_FOLDER / (pdf_file.stem + ".json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    print(f"  → {len(chunks)} chunks saved")

print("\nChunking complete!")