"""Structured logging configuration for the backend application with sensitive data masking."""

import logging
import re
import sys
from typing import List, Tuple, Pattern


class SensitiveDataFilter(logging.Filter):
    """Log filter that redacts credentials, authorization tokens, and API keys from log messages."""

    PATTERNS: List[Tuple[Pattern, str]] = [
        # Bearer tokens (JWTs, dev tokens, Keycloak tokens)
        (re.compile(r"(Bearer\s+)[A-Za-z0-9-_=.]+", re.IGNORECASE), r"\1[REDACTED]"),
        # Keycloak / OAuth authorization codes
        (re.compile(r"((?:code|code_verifier|refresh_token|access_token)=)[A-Za-z0-9-_=.]+", re.IGNORECASE), r"\1[REDACTED]"),
        # JSON / query param passwords and secrets
        (re.compile(r"((?:password|secret|client_secret)\s*[:=]\s*['\"]?)[^'\",\s]+(['\"]?)", re.IGNORECASE), r"\1[REDACTED]\2"),
        # Groq API Keys (gsk_...)
        (re.compile(r"(gsk_[A-Za-z0-9]{6})[A-Za-z0-9]+", re.IGNORECASE), r"\1...[REDACTED]"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        if record.args and isinstance(record.args, tuple):
            cleaned_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in self.PATTERNS:
                        arg = pattern.sub(replacement, arg)
                cleaned_args.append(arg)
            record.args = tuple(cleaned_args)
        return True


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configures application-wide logging with a standardized format and security filter."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.addFilter(SensitiveDataFilter())

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_format,
        handlers=[stdout_handler],
        force=True,
    )

    # Suppress overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(numeric_level)
    logging.getLogger("uvicorn.error").setLevel(numeric_level)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger = logging.getLogger("university_assistant")
    logger.setLevel(numeric_level)
    logger.addFilter(SensitiveDataFilter())
    return logger


logger = logging.getLogger("university_assistant")
logger.addFilter(SensitiveDataFilter())
