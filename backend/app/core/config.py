"""Application configuration management using Pydantic Settings.

Reads environment variables from system environment and optional .env file.
Provides strongly typed access to core, database, external services, and security settings.
"""

from functools import lru_cache
from typing import Optional, Any
import json
from urllib.parse import quote_plus
from pydantic import Field, field_validator, model_validator
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
        default="production",
        description="Runtime environment: development, staging, production, testing.",
    )
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode and verbose tracebacks.",
    )
    ENABLE_DEV_AUTH: bool = Field(
        default=False,
        description="Explicitly enables mock authentication for local development only; never allowed in production.",
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
    CORS_ORIGINS: Any = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed origins for Cross-Origin Resource Sharing.",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Allows CORS_ORIGINS to be provided as a comma-separated string, JSON string, or list."""
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(o).strip() for o in parsed if str(o).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in v_str.split(",") if origin.strip()]
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
    RATE_LIMIT_AUTH_RPM: int = Field(
        default=10,
        description="Maximum login, code exchange, and refresh requests per minute per client IP.",
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

    # PostgreSQL Read Replicas & Read-Your-Own-Writes Consistency (FR-DBSYNC-003)
    DB_READ_REPLICAS_ENABLED: bool = Field(
        default=True,
        description="Enable separate PostgreSQL read replicas. Disable for a single-node laptop/demo deployment.",
    )
    POSTGRES_REPLICA1_HOST: str = Field(default="localhost")
    POSTGRES_REPLICA1_PORT: int = Field(default=5433)
    POSTGRES_REPLICA2_HOST: str = Field(default="localhost")
    POSTGRES_REPLICA2_PORT: int = Field(default=5434)
    READ_YOUR_WRITES_WINDOW_SECONDS: float = Field(
        default=5.0,
        description="Duration (seconds) during which subsequent reads from a user are routed to Primary after a write.",
    )

    # Redis Cache & Distributed Locking (FR-CACHE-001, FR-CACHE-002, FR-CACHE-003)
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_DB: int = Field(default=0)
    CACHE_ENABLED: bool = Field(
        default=True,
        description="Enables Redis read-through caching for document listing, details, and admin stats.",
    )
    CACHE_DEFAULT_TTL_SECONDS: int = Field(
        default=60,
        description="Default expiration time for cached read data in seconds (FR-CACHE-003).",
    )
    CACHE_DOCUMENTS_LIST_TTL: int = Field(
        default=60,
        description="Expiration time in seconds for document list cache (FR-CACHE-001).",
    )
    CACHE_ADMIN_STATS_TTL: int = Field(
        default=60,
        description="Expiration time in seconds for admin dashboard stats cache.",
    )
    LOCK_DEFAULT_TIMEOUT_SECONDS: float = Field(
        default=5.0,
        description="Maximum seconds to wait to acquire a distributed lock before timing out.",
    )
    LOCK_DEFAULT_EXPIRE_SECONDS: float = Field(
        default=30.0,
        description="Lock expiration TTL (seconds) to prevent deadlock if process dies.",
    )

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
    KEYCLOAK_PUBLIC_URL: Optional[str] = Field(
        default=None,
        description="Public browser-facing Keycloak URL (e.g., http://localhost:8080).",
    )
    KEYCLOAK_REALM: str = Field(default="university-realm")
    KEYCLOAK_CLIENT_ID: str = Field(default="university-assistant-client")
    KEYCLOAK_CLIENT_SECRET: Optional[str] = Field(default=None)
    KEYCLOAK_ISSUER: Optional[str] = Field(
        default=None,
        description="Exact token issuer URL advertised by the Keycloak realm, including /realms/{realm}.",
    )
    KEYCLOAK_AUDIENCE: Optional[str] = Field(
        default=None,
        description="Expected JWT audience. Configure a Keycloak audience mapper for this value.",
    )
    KEYCLOAK_REDIRECT_URI: Optional[str] = Field(
        default=None,
        description="Exact browser OAuth callback URI accepted by this deployment.",
    )

    # LLM API (Groq)
    GROQ_API_KEY: Optional[str] = Field(default=None)
    GROQ_MODEL: str = Field(default="llama-3.1-8b-instant")

    # Embedding Model (CPU-friendly defaults for local Docker/Kubernetes demos)
    EMBEDDING_MODEL_NAME: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_BATCH_SIZE: int = Field(default=8, ge=1, le=32)
    EMBEDDING_NUM_THREADS: int = Field(default=1, ge=1, le=8)
    RAG_INGESTION_BATCH_SIZE: int = Field(default=8, ge=1, le=64)
    RAG_MAX_CONCURRENT_INGESTIONS: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Maximum simultaneous document ingestions per backend process.",
    )

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

    # Advanced RAG Parameters (Prompt 26)
    RAG_ENABLE_HYBRID_SEARCH: bool = Field(default=True, description="Enable hybrid dense vector + lexical scoring.")
    RAG_ENABLE_RERANKING: bool = Field(default=False, description="Enable candidate re-ranking (disabled by default to preserve RAM/CPU).")
    RAG_RERANK_CANDIDATES_K: int = Field(default=20, description="Initial candidate pool size for re-ranking.")
    RAG_ENABLE_GROUNDEDNESS_CHECK: bool = Field(default=True, description="Enable groundedness verification on generated answers.")
    RAG_GROUNDEDNESS_THRESHOLD: float = Field(default=0.60, description="Minimum factual overlap score to accept answer as grounded.")
    RAG_MAX_RAW_CONVERSATION_TURNS: int = Field(default=4, description="Maximum recent raw conversation turns to retain before summarizing.")

    @model_validator(mode="after")
    def validate_security_configuration(self):
        """Reject unsafe development settings when the service is deployed outside local development."""
        environment = self.ENVIRONMENT.strip().lower()
        if environment in ("production", "prod", "staging"):
            if self.ENABLE_DEV_AUTH:
                raise ValueError("ENABLE_DEV_AUTH must be false outside local development.")
            if self.DEBUG:
                raise ValueError("DEBUG must be false in staging and production.")
            if self.SESSION_COOKIE_SECURE is False:
                raise ValueError("SESSION_COOKIE_SECURE cannot be false outside local development.")
            required_secrets = {
                "POSTGRES_PASSWORD": self.POSTGRES_PASSWORD,
                "REDIS_PASSWORD": self.REDIS_PASSWORD,
                "QDRANT_API_KEY": self.QDRANT_API_KEY,
                "MINIO_SECRET_KEY": self.MINIO_SECRET_KEY,
                "KEYCLOAK_ISSUER": self.KEYCLOAK_ISSUER,
                "KEYCLOAK_AUDIENCE": self.KEYCLOAK_AUDIENCE,
                "KEYCLOAK_REDIRECT_URI": self.KEYCLOAK_REDIRECT_URI,
            }
            missing = [name for name, value in required_secrets.items() if not value or not str(value).strip()]
            if missing:
                raise ValueError("Missing required production security configuration: " + ", ".join(missing))
            if self.POSTGRES_PASSWORD == "postgres" or self.MINIO_SECRET_KEY == "minioadmin":
                raise ValueError("Default PostgreSQL/MinIO credentials are not permitted outside local development.")
        return self

    @property
    def is_cookie_secure(self) -> bool:
        """Determines whether cookies must require HTTPS transmission."""
        if self.SESSION_COOKIE_SECURE is not None:
            return self.SESSION_COOKIE_SECURE
        return self.ENVIRONMENT.lower() not in ("development", "testing")

    @property
    def sync_database_url(self) -> str:
        """Synchronous connection URL for Alembic migrations and synchronous drivers."""
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_database_url(self) -> str:
        """Asynchronous connection URL for async SQLAlchemy operations."""
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def primary_async_url(self) -> str:
        """Asynchronous connection URL for Primary (Read-Write)."""
        return self.async_database_url

    @property
    def replica1_async_url(self) -> str:
        """Asynchronous connection URL for Read Replica 1."""
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_REPLICA1_HOST}:{self.POSTGRES_REPLICA1_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def replica2_async_url(self) -> str:
        """Asynchronous connection URL for Read Replica 2."""
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_REPLICA2_HOST}:{self.POSTGRES_REPLICA2_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        """Connection URL for Redis client."""
        if self.REDIS_PASSWORD:
            return f"redis://:{quote_plus(self.REDIS_PASSWORD)}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def public_keycloak_url(self) -> str:
        """Public Keycloak URL returned to client-side browsers for OAuth redirects."""
        if self.KEYCLOAK_PUBLIC_URL:
            return self.KEYCLOAK_PUBLIC_URL.rstrip("/")
        if "://keycloak:" in self.KEYCLOAK_URL:
            return self.KEYCLOAK_URL.replace("://keycloak:", "://localhost:").rstrip("/")
        return self.KEYCLOAK_URL.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    """Singleton cached provider for application settings."""
    return Settings()
