"""Qdrant vector database client and collection management (C-PROC, C-RAGSVC).

Manages Qdrant collection creation, payload indexing, batch vector upsert,
duplicate prevention, point deletion, and top-k cosine similarity retrieval.
"""

import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.http import models

from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.core.errors import ExternalServiceError
from backend.app.rag.chunker import DocumentChunk

settings = get_settings()


class SearchResult(BaseModel):
    """Schema for a retrieved semantic chunk from Qdrant."""

    chunk_id: str = Field(..., description="Unique vector point identifier.")
    document_id: str = Field(..., description="Foreign key linking to PostgreSQL document record.")
    document_name: str = Field(..., description="Source document title.")
    chunk_text: str = Field(..., description="Text content of the retrieved chunk.")
    page: Optional[int] = Field(default=None, description="Source PDF page number (1-indexed).")
    section: Optional[str] = Field(default=None, description="Section heading context.")
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0).")
    category: Optional[str] = Field(default=None, description="Document category.")


class QdrantVectorStore:
    """Manages vector operations and schema within Qdrant."""

    def __init__(self):
        self.host = settings.QDRANT_HOST
        self.port = settings.QDRANT_PORT
        self.collection_name = settings.QDRANT_COLLECTION
        self.api_key = settings.QDRANT_API_KEY
        self.vector_dim = 384  # Matches sentence-transformers/all-MiniLM-L6-v2
        self._client: Optional[QdrantClient] = None

    @property
    def client(self) -> QdrantClient:
        """Lazy-loaded Qdrant client instance."""
        if self._client is None:
            try:
                self._client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    api_key=self.api_key,
                    timeout=10.0,
                )
            except Exception as exc:
                logger.error("Failed to initialize QdrantClient: %s", exc)
                raise ExternalServiceError("Qdrant", f"Initialization error: {exc}")
        return self._client

    def ensure_collection_exists(self) -> None:
        """Verifies collection exists with 384-dim Cosine configuration; creates it if absent."""
        try:
            collections_response = self.client.get_collections()
            existing_names = [col.name for col in collections_response.collections]

            if self.collection_name not in existing_names:
                logger.info(
                    "Creating Qdrant collection '%s' (dim=%d, distance=Cosine)...",
                    self.collection_name,
                    self.vector_dim,
                )
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_dim,
                        distance=models.Distance.COSINE,
                    ),
                )
                # Create payload indexes for fast filtered lookups
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="document_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="category",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                logger.info("Qdrant collection '%s' created with payload indexes.", self.collection_name)
        except Exception as exc:
            logger.error("Failed to verify/create Qdrant collection '%s': %s", self.collection_name, exc)
            raise ExternalServiceError("Qdrant", f"Collection check failed: {exc}")

    def upsert_chunks(
        self,
        document_id: uuid.UUID,
        document_title: str,
        category: str,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
    ) -> List[str]:
        """Upserts document chunks and embeddings into Qdrant.

        Uses deterministic vector UUIDs (uuid5) derived from document_id and chunk_index
        to strictly prevent duplicate points if a document is re-processed.

        Payload schema:
        - document_id: Foreign key to PostgreSQL documents.id
        - chunk_text: Text content of the chunk
        - page: 1-indexed source PDF page number
        - section: Section heading
        - document_name: Document title
        - chunk_id: Vector point identifier

        Returns:
            List of vector_id UUID strings corresponding to the upserted points.
        """
        self.ensure_collection_exists()

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks count ({len(chunks)}) does not match embeddings count ({len(embeddings)})"
            )

        points: List[models.PointStruct] = []
        vector_ids: List[str] = []

        for chunk, embedding in zip(chunks, embeddings):
            # Deterministic UUID prevents duplicate points under repeated execution
            vector_id = str(uuid.uuid5(document_id, f"chunk_{chunk.chunk_index}"))
            vector_ids.append(vector_id)

            payload: Dict[str, Any] = {
                # Prompt 8 required metadata fields:
                "document_id": str(document_id),
                "chunk_text": chunk.text,
                "page": chunk.page,
                "section": chunk.section,
                "document_name": document_title,
                "chunk_id": vector_id,
                # Context & backward compatibility fields:
                "text": chunk.text,
                "document_title": document_title,
                "category": category,
                "chunk_index": chunk.chunk_index,
                "char_count": chunk.char_count,
            }

            points.append(
                models.PointStruct(
                    id=vector_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
            logger.info("Upserted %d vector points to Qdrant for document '%s'", len(points), document_id)
            return vector_ids
        except Exception as exc:
            logger.error("Qdrant upsert failed for document '%s': %s", document_id, exc)
            raise ExternalServiceError("Qdrant", f"Vector upsert failed: {exc}")

    def delete_document_vectors(self, document_id: uuid.UUID) -> None:
        """Deletes all vector points associated with a specific document ID."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=str(document_id)),
                            )
                        ]
                    )
                ),
                wait=True,
            )
            logger.info("Deleted vectors for document '%s' from Qdrant.", document_id)
        except Exception as exc:
            logger.error("Failed to delete vectors for document '%s' from Qdrant: %s", document_id, exc)
            raise ExternalServiceError("Qdrant", f"Vector deletion failed: {exc}")

    def count_document_vectors(self, document_id: uuid.UUID) -> int:
        """Counts existing vector points for a given document ID."""
        try:
            result = self.client.count(
                collection_name=self.collection_name,
                count_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=str(document_id)),
                        )
                    ]
                ),
            )
            return result.count
        except Exception as exc:
            logger.error("Failed to count vectors for document '%s': %s", document_id, exc)
            return 0

    def search_vectors(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filter_category: Optional[str] = None,
        filter_document_id: Optional[uuid.UUID] = None,
    ) -> List[SearchResult]:
        """Executes top-k cosine similarity search against Qdrant collection."""
        self.ensure_collection_exists()

        must_conditions = []
        if filter_category:
            must_conditions.append(
                models.FieldCondition(
                    key="category",
                    match=models.MatchValue(value=filter_category),
                )
            )
        if filter_document_id:
            must_conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=str(filter_document_id)),
                )
            )

        query_filter = models.Filter(must=must_conditions) if must_conditions else None

        try:
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit,
                    query_filter=query_filter,
                    score_threshold=score_threshold,
                    with_payload=True,
                )
                hits = response.points
            else:
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    query_filter=query_filter,
                    score_threshold=score_threshold,
                    with_payload=True,
                )

            results: List[SearchResult] = []
            for hit in hits:
                payload = hit.payload or {}
                results.append(
                    SearchResult(
                        chunk_id=str(hit.id),
                        document_id=payload.get("document_id", ""),
                        document_name=payload.get("document_name") or payload.get("document_title", ""),
                        chunk_text=payload.get("chunk_text") or payload.get("text", ""),
                        page=payload.get("page"),
                        section=payload.get("section"),
                        score=round(float(hit.score), 4),
                        category=payload.get("category"),
                    )
                )
            return results
        except Exception as exc:
            logger.error("Qdrant vector search failed: %s", exc)
            raise ExternalServiceError("Qdrant", f"Vector search failed: {exc}")

    def search(
        self,
        query: str,
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filter_category: Optional[str] = None,
        filter_document_id: Optional[uuid.UUID] = None,
    ) -> List[SearchResult]:
        """Encodes query with all-MiniLM-L6-v2 and retrieves top-k most similar chunks."""
        from backend.app.rag.embeddings import embedding_client

        query_vector = embedding_client.embed_query(query)
        return self.search_vectors(
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            filter_category=filter_category,
            filter_document_id=filter_document_id,
        )


vector_store = QdrantVectorStore()
