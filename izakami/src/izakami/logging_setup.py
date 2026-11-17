"""Local file logging. Technical details go here, not in front of the user."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .paths import log_path


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("izakami")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    try:
        handler: logging.Handler = RotatingFileHandler(
            log_path(), maxBytes=512_000, backupCount=2, encoding="utf-8"
        )
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger
