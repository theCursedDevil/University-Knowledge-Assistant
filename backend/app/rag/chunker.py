"""Recursive character text chunking module using LangChain (C-PROC).

Segments extracted pages into ~500-800 token chunks (~2000-3200 characters)
with ~100 token overlap (~400 characters), associating chunk index, page number,
and section heading.
"""

from typing import List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from backend.app.rag.extractor import ExtractedPage
from backend.app.core.logging import logger

# Token-to-character ratio approximation: 1 token ≈ 4 characters in English
DEFAULT_CHUNK_SIZE_TOKENS = 700
DEFAULT_CHUNK_OVERLAP_TOKENS = 100

DEFAULT_CHUNK_SIZE_CHARS = DEFAULT_CHUNK_SIZE_TOKENS * 4      # 2800 characters (~700 tokens)
DEFAULT_CHUNK_OVERLAP_CHARS = DEFAULT_CHUNK_OVERLAP_TOKENS * 4  # 400 characters (~100 tokens)


class DocumentChunk(BaseModel):
    """Container for a single semantic chunk ready for embedding and indexing."""

    chunk_index: int = Field(..., description="0-indexed sequence position within document.")
    text: str = Field(..., description="Chunk text content.")
    page: int = Field(..., description="Source PDF page number.")
    section: Optional[str] = Field(default=None, description="Active section title at chunk location.")
    char_count: int = Field(..., description="Character count of chunk text.")


def create_text_splitter(
    chunk_size_chars: int = DEFAULT_CHUNK_SIZE_CHARS,
    chunk_overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
) -> RecursiveCharacterTextSplitter:
    """Instantiates a LangChain RecursiveCharacterTextSplitter with semantic separators."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_chars,
        chunk_overlap=chunk_overlap_chars,
        separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
        keep_separator=True,
    )


def chunk_document_pages(
    pages: List[ExtractedPage],
    chunk_size_chars: int = DEFAULT_CHUNK_SIZE_CHARS,
    chunk_overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
) -> List[DocumentChunk]:
    """Splits extracted document pages into semantic chunks while preserving source page provenance.

    Args:
        pages: List of ExtractedPage from extractor.
        chunk_size_chars: Maximum characters per chunk (~700 tokens).
        chunk_overlap_chars: Overlapping characters between adjacent chunks (~100 tokens).

    Returns:
        List of DocumentChunk instances.
    """
    splitter = create_text_splitter(chunk_size_chars, chunk_overlap_chars)
    chunks: List[DocumentChunk] = []
    chunk_index = 0

    for page in pages:
        # If page text is within chunk size, keep as single chunk
        if len(page.text) <= chunk_size_chars:
            chunks.append(
                DocumentChunk(
                    chunk_index=chunk_index,
                    text=page.text,
                    page=page.page_number,
                    section=page.section,
                    char_count=len(page.text),
                )
            )
            chunk_index += 1
        else:
            # Split page text into overlapping windows
            page_chunks = splitter.split_text(page.text)
            for text_piece in page_chunks:
                clean_piece = text_piece.strip()
                if clean_piece:
                    chunks.append(
                        DocumentChunk(
                            chunk_index=chunk_index,
                            text=clean_piece,
                            page=page.page_number,
                            section=page.section,
                            char_count=len(clean_piece),
                        )
                    )
                    chunk_index += 1

    logger.info("Chunked %d pages into %d chunks.", len(pages), len(chunks))
    return chunks
