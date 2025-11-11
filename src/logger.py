"""
Configuration du système de logging structuré avec structlog.
"""

import logging
import sys
from typing import Any, Dict

import structlog


def setup_logging(level: str = "info", log_format: str = "json") -> None:
    """
    Configure le système de logging structuré.
    
    Args:
        level: Niveau de log (debug, info, warning, error)
        log_format: Format de sortie (json ou console)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configuration de base
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
        structlog.processors.StackInfoRenderer(),
    ]
    
    # Choix du renderer selon le format
    if log_format == "json":
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer()
        ]
    
    # Configuration de structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """
    Récupère un logger structuré.
    
    Args:
        name: Nom du logger (généralement __name__)
        
    Returns:
        Logger structlog
    """
    return structlog.get_logger(name)


def log_context(**kwargs: Any) -> Dict[str, Any]:
    """
    Ajoute du contexte aux logs suivants.
    
    Args:
        **kwargs: Paires clé-valeur à ajouter au contexte
        
    Returns:
        Contexte ajouté
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(**kwargs)
    return kwargs