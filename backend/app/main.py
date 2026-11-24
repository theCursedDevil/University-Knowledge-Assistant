"""FastAPI application factory and main entry point.

Configures CORS middleware, exception handlers, Swagger/OpenAPI documentation,
lifecycle logging, and routes.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.config import get_settings
from backend.app.core.security import token_validator
from backend.app.core.logging import setup_logging, logger
from backend.app.core.errors import (
    AppException,
    ErrorDetail,
    ErrorResponse,
)
from backend.app.core.metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_ERRORS_TOTAL,
    get_metrics_payload,
    update_postgres_replication_lag,
)
from backend.app.api.router import api_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and graceful shutdown events."""
    setup_logging(settings.LOG_LEVEL)
    logger.info(
        "Starting %s v%s [Env: %s, Debug: %s]",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
        settings.DEBUG,
    )

    # 1. Background warmup for SentenceTransformer embedding model and Qdrant
    # Allows HTTP healthcheck probes to succeed instantly without Kubelet timeout
    import asyncio

    def _warmup_sync() -> None:
        try:
            from backend.app.rag.embeddings import embedding_client
            from backend.app.rag.vector_store import vector_store

            logger.info("Background warming up SentenceTransformer '%s' on CPU...", settings.EMBEDDING_MODEL_NAME)
            _ = embedding_client.model
            logger.info("Verifying Qdrant vector collection '%s'...", settings.QDRANT_COLLECTION)
            vector_store.ensure_collection_exists()
            logger.info("Embedding model and Qdrant vector store successfully initialized.")
        except Exception as exc:
            logger.warning("Startup AI model background pre-initialization deferred: %s", exc)

    async def _warmup_ai_models() -> None:
        try:
            await asyncio.to_thread(_warmup_sync)
        except Exception as exc:
            logger.warning("Async model warmup task deferred: %s", exc)

    asyncio.create_task(_warmup_ai_models())

    # 2. Verify Redis cache & locking client connectivity (C-CACHE)
    try:
        from backend.app.core.cache import redis_manager
        redis_healthy = await asyncio.to_thread(redis_manager.is_healthy)
        if redis_healthy:
            logger.info("Connected to Redis cache at %s:%s (db=%s).", settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
        else:
            logger.warning("Redis cache at %s:%s is currently unreachable; operating in graceful fallback mode.", settings.REDIS_HOST, settings.REDIS_PORT)
    except Exception as exc:
        logger.warning("Redis initialization check deferred: %s", exc)

    # 3. Verify MinIO knowledge storage bucket exists (C-DOCSVC)
    try:
        from backend.app.services.storage import storage_service
        await asyncio.to_thread(storage_service.ensure_bucket_exists)
        logger.info("MinIO storage bucket '%s' verified.", settings.MINIO_BUCKET_NAME)
    except Exception as exc:
        logger.warning("MinIO bucket initialization deferred: %s", exc)

    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


def create_app() -> FastAPI:
    """Application factory building and configuring the FastAPI instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "Generative AI-Based University Knowledge Assistant Backend API. "
            "Provides grounded RAG question answering, document ingestion, "
            "and multi-replica synchronization."
        ),
        docs_url="/docs" if settings.ENVIRONMENT.lower() in ("development", "testing") else None,
        redoc_url="/redoc" if settings.ENVIRONMENT.lower() in ("development", "testing") else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT.lower() in ("development", "testing") else None,
        swagger_ui_init_oauth={
            "clientId": settings.KEYCLOAK_CLIENT_ID,
            "usePkceWithAuthorizationCodeGrant": True,
            "appName": "University Knowledge Assistant API",
            "scopes": ["openid", "profile", "email"],
        },
        lifespan=lifespan,
    )

    # Authenticate document uploads before Starlette/FastAPI parses multipart
    # bodies. A mere header-presence check is not enough: an unauthenticated client
    # could otherwise add a bogus Bearer value and still reach the multipart parser.
    @app.middleware("http")
    async def early_upload_auth_middleware(request: Request, call_next):
        normalized_path = request.url.path.rstrip("/")
        is_upload = request.method == "POST" and normalized_path == f"{settings.API_V1_PREFIX}/documents"
        if is_upload and settings.ENVIRONMENT.lower() != "testing":
            authorization = request.headers.get("authorization", "")
            raw_token = (
                authorization[7:].strip()
                if authorization.lower().startswith("bearer ")
                else request.cookies.get("uka_access_token", "")
            )
            valid_local_token = (
                raw_token.startswith("dev-token-")
                and settings.ENVIRONMENT.lower() == "development"
                and settings.ENABLE_DEV_AUTH
            )
            if not raw_token:
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "UNAUTHORIZED", "message": "Authentication is required."}},
                )
            if not valid_local_token:
                try:
                    await asyncio.to_thread(token_validator.validate_token, raw_token)
                except Exception:
                    return JSONResponse(
                        status_code=401,
                        content={"error": {"code": "UNAUTHORIZED", "message": "A valid session is required."}},
                    )
        return await call_next(request)

    # 1. CORS Middleware (Restricted to Authorized Frontend Origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Database-Route", "X-Database-Route-Reason", "X-Cache"],
    )

    # 2. Database Routing Headers Middleware (FR-DBSYNC-002, FR-DBSYNC-003)
    @app.middleware("http")
    async def db_routing_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        db_route = getattr(request.state, "db_route", None)
        if db_route:
            response.headers["X-Database-Route"] = db_route
            db_reason = getattr(request.state, "db_route_reason", None)
            if db_reason:
                response.headers["X-Database-Route-Reason"] = db_reason
        return response

    # 3. HTTP Security Headers Middleware (OWASP Secure Headers, HSTS, Permissions Policy)
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if settings.ENVIRONMENT.lower() not in ("development", "testing"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        return response

    # 4. Prometheus Application Metrics Middleware (C-MON, FR-MON, Prompt 27)
    @app.middleware("http")
    async def prometheus_metrics_middleware(request: Request, call_next):
        # Avoid collecting metrics on Prometheus scrape endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.perf_counter()
        method = request.method
        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time
            route = request.scope.get("route")
            endpoint = getattr(route, "path", "/unmatched")
            status_code = str(response.status_code)

            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)
            if response.status_code >= 400:
                HTTP_ERRORS_TOTAL.labels(method=method, endpoint=endpoint, status_code=status_code).inc()

            return response
        except Exception:
            duration = time.perf_counter() - start_time
            route = request.scope.get("route")
            endpoint = getattr(route, "path", "/unmatched")
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code="500").inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)
            HTTP_ERRORS_TOTAL.labels(method=method, endpoint=endpoint, status_code="500").inc()
            raise

    # 4. Global Exception Handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "Domain error [%s] %s on %s %s: %s",
            exc.code,
            exc.status_code,
            request.method,
            request.url.path,
            exc.message,
        )
        resp_headers = {}
        if exc.status_code == 429:
            retry_after = 60
            if isinstance(exc.details, dict) and "retry_after" in exc.details:
                retry_after = exc.details["retry_after"]
            elif hasattr(exc, "retry_after"):
                retry_after = exc.retry_after
            resp_headers["Retry-After"] = str(retry_after)

        return JSONResponse(
            status_code=exc.status_code,
            headers=resp_headers if resp_headers else None,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                    details=exc.details,
                )
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info(
            "Validation error on %s %s: %s",
            request.method,
            request.url.path,
            exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message="Request validation failed. Verify input schema.",
                    details=exc.errors(),
                )
            ).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = "HTTP_ERROR"
        if exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 401:
            code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=code,
                    message=str(exc.detail),
                )
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc)
        response_headers = {}
        origin = request.headers.get("origin")
        if origin and origin in settings.CORS_ORIGINS:
            response_headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Vary": "Origin",
            }
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers=response_headers,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INTERNAL_SERVER_ERROR",
                    message="An unexpected server error occurred.",
                    details=None,
                )
            ).model_dump(),
        )

    # Mount all application routes once under the versioned API prefix.
    # The metrics endpoint below is intentionally separate for Prometheus scraping.
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # 5. Prometheus Scrape Endpoint (C-MON, FR-MON, Prompt 27)
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint():
        await update_postgres_replication_lag()
        payload, content_type = get_metrics_payload()
        return Response(content=payload, media_type=content_type)

    return app


# Application entry point for Uvicorn ASGI server
app = create_app()
