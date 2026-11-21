"""RAG and document processing package (C-PROC, C-RAGSVC).

Provides text extraction, cleaning, chunking, embeddings, vector storage, pipeline orchestration,
prompt assembly, vector retrieval, and end-to-end question answering.
"""

from backend.app.rag.extractor import ExtractedPage, clean_text, extract_text_from_pdf
from backend.app.rag.chunker import DocumentChunk, chunk_document_pages
from backend.app.rag.embeddings import EmbeddingClient, embedding_client
from backend.app.rag.vector_store import QdrantVectorStore, vector_store, SearchResult
from backend.app.rag.pipeline import ProcessingResult, process_document
from backend.app.rag.prompt import build_rag_prompt
from backend.app.rag.retriever import VectorRetriever, vector_retriever, RetrievalResult
from backend.app.rag.llm import LLMClient, llm_client
from backend.app.rag.citation import Citation, CitationResolver, citation_resolver
from backend.app.rag.rag_service import RAGService, rag_service, RAGResponse

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
    "SearchResult",
    "ProcessingResult",
    "process_document",
    "build_rag_prompt",
    "VectorRetriever",
    "vector_retriever",
    "RetrievalResult",
    "LLMClient",
    "llm_client",
    "Citation",
    "CitationResolver",
    "citation_resolver",
    "RAGService",
    "rag_service",
    "RAGResponse",
]
