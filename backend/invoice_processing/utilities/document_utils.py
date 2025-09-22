# Copyright 2024 Artificial Intelligence Labs, SL

"""
Document utilities - SIMPLE and FOCUSED
One responsibility: handle document metadata and hashing
"""

import io
import hashlib
from typing import Dict, Any
from pydantic import BaseModel
from pypdf import PdfReader
from loguru import logger


class DocumentPageSize(BaseModel):
    """Document page size information."""
    width: float
    height: float

    @classmethod
    def from_mediabox(cls, mediabox) -> "DocumentPageSize":
        """Create from PDF mediabox."""
        return cls(
            width=float(mediabox[2] - mediabox[0]),
            height=float(mediabox[3] - mediabox[1])
        )


class DocumentInfo(BaseModel):
    """Document metadata information."""
    hash: str
    num_pages: int
    page_size: DocumentPageSize


class DocumentUtilities:
    """
    Simple utilities for document processing.
    Handles file hashing and metadata extraction.
    """

    @staticmethod
    def calculate_file_hash(file_bytes: bytes) -> str:
        """
        Calculate SHA256 hash of file bytes.

        Args:
            file_bytes: The file content as bytes

        Returns:
            The SHA256 hash as hexadecimal string
        """
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def extract_document_info(file_bytes: bytes, file_hash: str) -> DocumentInfo:
        """
        Extract document metadata from PDF bytes.

        Args:
            file_bytes: The PDF file content as bytes
            file_hash: The calculated file hash

        Returns:
            DocumentInfo object with metadata
        """
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            num_pages = len(reader.pages)

            # Get page size from first page
            if num_pages > 0:
                page_size = DocumentPageSize.from_mediabox(reader.pages[0].mediabox)
            else:
                page_size = DocumentPageSize(width=0, height=0)

            return DocumentInfo(
                hash=file_hash,
                num_pages=num_pages,
                page_size=page_size
            )

        except Exception as e:
            logger.warning(f"Could not extract document info: {e}")
            return DocumentInfo(
                hash=file_hash,
                num_pages=0,
                page_size=DocumentPageSize(width=0, height=0)
            )


# Global utilities instance
document_utils = DocumentUtilities()