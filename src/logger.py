"""
Configuration du système de logging avec structlog.
Fournit des logs structurés au format JSON.
"""

import logging
import sys

import structlog


def setup_logger(level: str = "info", format: str = "json") -> structlog.BoundLogger:
    """
    Configure le système de logging avec structlog.

    Args:
        level: Niveau de log (debug, info, warning, error)
        format: Format des logs (json ou console)

    Returns:
        Logger structlog configuré
    """
    # Mapper les niveaux de log
    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }

    log_level = log_levels.get(level.lower(), logging.INFO)

    # Configuration du logging standard Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Processeurs communs
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]

    # Processeurs selon le format
    if format == "json":
        # Format JSON pour production
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Format console pour développement
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ]

    # Configuration structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Retourner le logger
    logger = structlog.get_logger()

    logger.info(
        "Logger configuré",
        extra={
            "level": level,
            "format": format,
        },
    )

    return logger


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Récupère un logger structlog.

    Args:
        name: Nom du logger (optionnel)

    Returns:
        Logger structlog
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()