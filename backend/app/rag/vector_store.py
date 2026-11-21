"""Qdrant vector database client and collection management (C-PROC, C-RAGSVC).

Manages Qdrant collection creation, payload indexing, batch vector upsert,
and document-level point deletion.
"""

import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models

from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.core.errors import ExternalServiceError
from backend.app.rag.chunker import DocumentChunk

settings = get_settings()


class QdrantVectorStore:
    """Manages vector operations and schema within Qdrant."""

    def __init__(self):
        self.host = settings.QDRANT_HOST
        self.port = settings.QDRANT_PORT
        self.collection_name = settings.QDRANT_COLLECTION
        self.api_key = settings.QDRANT_API_KEY
        self.vector_dim = 384
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
        """Upserts a list of document chunks and their embeddings into Qdrant.

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
            vector_id = str(uuid.uuid4())
            vector_ids.append(vector_id)

            payload: Dict[str, Any] = {
                "document_id": str(document_id),
                "document_title": document_title,
                "category": category,
                "chunk_index": chunk.chunk_index,
                "page": chunk.page,
                "section": chunk.section,
                "text": chunk.text,
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


vector_store = QdrantVectorStore()
