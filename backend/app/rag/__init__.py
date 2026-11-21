"""RAG and document processing package (C-PROC, C-RAGSVC).

Provides text extraction, cleaning, chunking, embeddings, vector storage, and pipeline orchestration.
"""

from backend.app.rag.extractor import ExtractedPage, clean_text, extract_text_from_pdf
from backend.app.rag.chunker import DocumentChunk, chunk_document_pages
from backend.app.rag.embeddings import EmbeddingClient, embedding_client
from backend.app.rag.vector_store import QdrantVectorStore, vector_store
from backend.app.rag.pipeline import ProcessingResult, process_document

__all__ = [
    "ExtractedPage",
    "clean_text",
    "extract_text_from_pdf",
    "DocumentChunk",
    "chunk_document_pages",
    "EmbeddingClient",
    "embedding_client",
    "QdrantVectorStore",
    "vector_store",
    "ProcessingResult",
    "process_document",
]
