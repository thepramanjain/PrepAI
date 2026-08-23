"""
app/utils/resume_parser.py

Utility functions to parse text from resumes (PDF and DOCX).
"""

import io
import re

import fitz  # PyMuPDF
import docx

def _clean_text(text: str) -> str:
    """
    Remove excessive whitespace from extracted text.
    Preserves single newlines (paragraph separation) but collapses
    multiple newlines and spaces.
    """
    # Replace multiple spaces with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Replace 3 or more newlines with 2 newlines (paragraph break)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract plain text from a PDF file using PyMuPDF.
    """
    text = ""
    # Open the PDF from memory
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
            
    return _clean_text(text)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract plain text from a DOCX file using python-docx.
    """
    text = ""
    # Open the DOCX from memory
    doc = docx.Document(io.BytesIO(file_bytes))
    for para in doc.paragraphs:
        if para.text.strip():
            text += para.text + "\n"
            
    return _clean_text(text)
