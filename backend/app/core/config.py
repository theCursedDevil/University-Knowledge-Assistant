"""Application configuration management using Pydantic Settings.

Reads environment variables from system environment and optional .env file.
Provides strongly typed access to core, database, external services, and security settings.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration class for the University Knowledge Assistant backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Application
    PROJECT_NAME: str = Field(
        default="University Knowledge Assistant API",
        description="Public title for the API and Swagger documentation.",
    )
    VERSION: str = Field(
        default="0.1.0",
        description="Semantic version of the application.",
    )
    ENVIRONMENT: str = Field(
        default="development",
        description="Runtime environment: development, staging, production, testing.",
    )
    DEBUG: bool = Field(
        default=True,
        description="Enable debug mode and verbose tracebacks.",
    )
    API_V1_PREFIX: str = Field(
        default="/api/v1",
        description="URL prefix for version 1 API routes.",
    )
    HOST: str = Field(
        default="0.0.0.0",
        description="Host interface to bind the application server.",
    )
    PORT: int = Field(
        default=8000,
        description="Port for the application server.",
    )

    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Standard logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL.",
    )

    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed origins for Cross-Origin Resource Sharing.",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Allows CORS_ORIGINS to be provided as a comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(origin).strip() for origin in v if str(origin).strip()]
        return v

    # Rate Limiting (NFR-SEC-004)
    RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        description="Enforces request rate limiting on LLM/compute intensive endpoints.",
    )
    RATE_LIMIT_LLM_RPM: int = Field(
        default=20,
        description="Maximum allowed LLM requests per minute per user/IP address.",
    )

    # Cookie & HTTPS Security (NFR-SEC-001)
    SESSION_COOKIE_SECURE: Optional[bool] = Field(
        default=None,
        description="Enforces HTTPS-only transmission for session cookies. If None, auto-enabled in non-dev environments.",
    )

    # PostgreSQL Primary (Read-Write)
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="postgres")
    POSTGRES_DB: str = Field(default="university_assistant")

    # PostgreSQL Read Replicas
    POSTGRES_REPLICA1_HOST: str = Field(default="localhost")
    POSTGRES_REPLICA1_PORT: int = Field(default=5432)
    POSTGRES_REPLICA2_HOST: str = Field(default="localhost")
    POSTGRES_REPLICA2_PORT: int = Field(default=5432)

    # Redis Cache & Distributed Locking
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_DB: int = Field(default=0)

    # Qdrant Vector Database
    QDRANT_HOST: str = Field(default="localhost")
    QDRANT_PORT: int = Field(default=6333)
    QDRANT_COLLECTION: str = Field(default="university_documents")
    QDRANT_API_KEY: Optional[str] = Field(default=None)

    # MinIO Object Storage
    MINIO_ENDPOINT: str = Field(default="localhost:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="minioadmin")
    MINIO_BUCKET_NAME: str = Field(default="university-documents")
    MINIO_SECURE: bool = Field(default=False)
    MAX_UPLOAD_SIZE_BYTES: int = Field(
        default=25 * 1024 * 1024,
        description="Maximum allowed file upload size in bytes (default: 25 MB).",
    )

    # Keycloak OIDC Authentication
    KEYCLOAK_URL: str = Field(default="http://localhost:8080")
    KEYCLOAK_REALM: str = Field(default="university-realm")
    KEYCLOAK_CLIENT_ID: str = Field(default="university-assistant-client")
    KEYCLOAK_CLIENT_SECRET: Optional[str] = Field(default=None)

    # LLM API (Groq)
    GROQ_API_KEY: Optional[str] = Field(default=None)
    GROQ_MODEL: str = Field(default="llama-3.1-8b-instant")

    # Embedding Model
    EMBEDDING_MODEL_NAME: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")

    # RAG Generation & Grounding Parameters
    RAG_TOP_K: int = Field(default=5, description="Default number of chunks retrieved per question.")
    RAG_CONFIDENCE_THRESHOLD: float = Field(
        default=0.30,
        description="Minimum cosine similarity required for relevant chunk gating.",
    )
    RAG_LLM_TEMPERATURE: float = Field(
        default=0.1,
        description="Low temperature generation (0.0 to 0.3) for factual grounded answers.",
    )
    RAG_INSUFFICIENT_CONTEXT_MESSAGE: str = Field(
        default="I couldn't find sufficient information about this in the available university documents.",
        description="Standard fallback response when retrieval confidence is insufficient.",
    )

    @property
    def is_cookie_secure(self) -> bool:
        """Determines whether cookies must require HTTPS transmission."""
        if self.SESSION_COOKIE_SECURE is not None:
            return self.SESSION_COOKIE_SECURE
        return self.ENVIRONMENT.lower() not in ("development", "testing")

    @property
    def sync_database_url(self) -> str:
        """Synchronous connection URL for Alembic migrations and synchronous drivers."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_database_url(self) -> str:
        """Asynchronous connection URL for async SQLAlchemy operations."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def replica1_async_url(self) -> str:
        """Asynchronous connection URL for Read Replica 1."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_REPLICA1_HOST}:{self.POSTGRES_REPLICA1_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def replica2_async_url(self) -> str:
        """Asynchronous connection URL for Read Replica 2."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_REPLICA2_HOST}:{self.POSTGRES_REPLICA2_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        """Connection URL for Redis client."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """Singleton cached provider for application settings."""
    return Settings()
