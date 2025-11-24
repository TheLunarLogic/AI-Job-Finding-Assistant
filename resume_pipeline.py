"""Resume text extraction pipeline for PDF, DOCX, and TXT files."""
import os
from typing import Optional
import io

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file content."""
    if not PDF_AVAILABLE:
        raise ImportError("PyPDF2 is required for PDF processing. Install it with: pip install PyPDF2")
    
    pdf_file = io.BytesIO(file_content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    
    return text.strip()


def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file content."""
    if not DOCX_AVAILABLE:
        raise ImportError("python-docx is required for DOCX processing. Install it with: pip install python-docx")
    
    doc_file = io.BytesIO(file_content)
    doc = Document(doc_file)
    
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    
    return text.strip()


def extract_text_from_txt(file_content: bytes) -> str:
    """Extract text from TXT file content."""
    try:
        # Try UTF-8 first
        return file_content.decode('utf-8').strip()
    except UnicodeDecodeError:
        # Fallback to latin-1
        return file_content.decode('latin-1').strip()


def extract_resume_text(file_content: bytes, filename: str) -> str:
    """
    Extract text from resume file based on file extension.
    
    Args:
        file_content: Binary content of the file
        filename: Original filename with extension
        
    Returns:
        Extracted text content
    """
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf'):
        return extract_text_from_pdf(file_content)
    elif filename_lower.endswith('.docx') or filename_lower.endswith('.doc'):
        return extract_text_from_docx(file_content)
    elif filename_lower.endswith('.txt'):
        return extract_text_from_txt(file_content)
    else:
        raise ValueError(f"Unsupported file type: {filename}. Supported formats: PDF, DOCX, TXT")

