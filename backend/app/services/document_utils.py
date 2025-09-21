# Copyright 2024 Artificial Intelligence Labs, SL

import io
import hashlib
from pypdf import PdfReader
from app.rest.models import DocumentInfo, DocumentPageSize


def calculate_file_hash(file_bytes: bytes) -> str:
    """
    Calculate SHA256 hash of file bytes.

    Args:
        file_bytes: The file content as bytes

    Returns:
        The SHA256 hash as hexadecimal string
    """
    return hashlib.sha256(file_bytes).hexdigest()


def extract_document_info(file_bytes: bytes, file_hash: str) -> DocumentInfo:
    """
    Extract document metadata from PDF bytes.

    Args:
        file_bytes: The PDF file content as bytes
        file_hash: The calculated file hash

    Returns:
        DocumentInfo with extracted metadata
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    page = reader.pages[0]

    return DocumentInfo(
        hash=file_hash,
        num_pages=len(reader.pages),
        page_size=DocumentPageSize.from_mediabox(page.mediabox),
    )