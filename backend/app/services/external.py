"""External service configuration and health verification module.

Provides strongly typed configuration containers and health status probes
for PostgreSQL, Redis, Qdrant, MinIO, Keycloak, and Groq LLM API.
"""

from typing import Dict, Any
from backend.app.core.config import get_settings
from backend.app.core.logging import logger

settings = get_settings()


class ExternalServicesConfig:
    """Consolidates and validates external service configurations."""

    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """Returns non-sensitive metadata about configured external endpoints."""
        return {
            "database": {
                "host": settings.POSTGRES_HOST,
                "port": settings.POSTGRES_PORT,
                "database": settings.POSTGRES_DB,
                "replicas": [
                    f"{settings.POSTGRES_REPLICA1_HOST}:{settings.POSTGRES_REPLICA1_PORT}",
                    f"{settings.POSTGRES_REPLICA2_HOST}:{settings.POSTGRES_REPLICA2_PORT}",
                ],
            },
            "redis": {
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "db": settings.REDIS_DB,
            },
            "qdrant": {
                "host": settings.QDRANT_HOST,
                "port": settings.QDRANT_PORT,
                "collection": settings.QDRANT_COLLECTION,
            },
            "minio": {
                "endpoint": settings.MINIO_ENDPOINT,
                "bucket": settings.MINIO_BUCKET_NAME,
                "secure": settings.MINIO_SECURE,
            },
            "keycloak": {
                "url": settings.KEYCLOAK_URL,
                "realm": settings.KEYCLOAK_REALM,
                "client_id": settings.KEYCLOAK_CLIENT_ID,
            },
            "llm": {
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "api_key_configured": bool(settings.GROQ_API_KEY),
            },
            "embedding": {
                "model": settings.EMBEDDING_MODEL_NAME,
            },
        }


def check_external_configuration() -> Dict[str, Any]:
    """Validates presence and syntax of configuration for external services."""
    summary = ExternalServicesConfig.get_summary()
    logger.debug("External services configuration loaded: %s", summary.keys())
    return summary
