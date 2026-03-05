"""Logging configuration for the CLI. Library users manage their own handlers."""
import logging
import os


def configure_logging() -> None:
    """Set up StreamHandler to stderr. Reads LOG_LEVEL env var (default INFO). Idempotent."""
    raw_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, raw_level, logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        return  # already configured
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)
