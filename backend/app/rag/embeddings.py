"""Embedding client using Sentence Transformers (all-MiniLM-L6-v2) (C-PROC, C-RAGSVC).

Produces 384-dimensional dense vectors with cosine normalization on local CPU.
"""

import threading
from typing import List, Optional
from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.core.errors import ExternalServiceError

settings = get_settings()


class EmbeddingClient:
    """Wrapper for SentenceTransformer embedding model."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.dimension = 384
        self._model = None
        self._lock = threading.Lock()
        self._encode_lock = threading.Lock()

    @property
    def model(self):
        """Lazy-loads the SentenceTransformer model on CPU with thread-safety."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        from sentence_transformers import SentenceTransformer
                        import torch

                        # Keep CPU inference predictable on memory-constrained laptops and
                        # small Kubernetes nodes. Environment variables in the containers
                        # reinforce these limits for BLAS/tokenizer worker pools.
                        torch.set_num_threads(settings.EMBEDDING_NUM_THREADS)
                        try:
                            torch.set_num_interop_threads(1)
                        except RuntimeError:
                            # PyTorch only allows this before parallel work starts.
                            pass

                        logger.info("Loading SentenceTransformer model '%s' on CPU...", self.model_name)
                        self._model = SentenceTransformer(self.model_name, device="cpu")
                        logger.info("Model '%s' loaded successfully.", self.model_name)
                    except Exception as exc:
                        logger.error("Failed to load SentenceTransformer '%s': %s", self.model_name, exc)
                        raise ExternalServiceError("EmbeddingModel", f"Model load failure: {exc}")
        return self._model

    def embed_texts(self, texts: List[str], batch_size: Optional[int] = None) -> List[List[float]]:
        """Encodes a bounded batch of texts into normalized 384-dimensional vectors."""
        if not texts:
            return []

        effective_batch_size = max(1, min(batch_size or settings.EMBEDDING_BATCH_SIZE, 32))
        try:
            # Serialize model inference within this backend process so concurrent chat
            # requests cannot multiply CPU/RAM use on a small laptop.
            with self._encode_lock:
                embeddings = self.model.encode(
                    texts,
                    batch_size=effective_batch_size,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )
            return embeddings.tolist()
        except Exception as exc:
            logger.error("Embedding generation failed for %d texts: %s", len(texts), exc)
            raise ExternalServiceError("EmbeddingModel", f"Embedding generation failed: {exc}")

    def embed_query(self, query: str) -> List[float]:
        """Encodes a single search query string."""
        if not query or not query.strip():
            return [0.0] * self.dimension

        result = self.embed_texts([query])
        return result[0]


embedding_client = EmbeddingClient()
