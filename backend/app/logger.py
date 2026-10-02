import logging
import sys
import structlog
from .config import settings

def configure_logging():
    """Configure structured logging for the whole application.
    Uses `structlog` to emit JSON‑compatible logs that also work with the
    standard `logging` library. All modules can simply do ``logger = structlog.get_logger()``.
    """
    # Basic logging configuration (stdout)
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Ensure root logger uses structlog's formatter
    logger = structlog.get_logger()
    return logger

# Initialise at import time so the configuration is ready for any module that imports this file.
logger = configure_logging()
