"""Unit tests for configure_logging()."""

import logging
import os
from unittest.mock import patch


def _reset_root_logger() -> None:
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    root.setLevel(logging.WARNING)


def test_handler_added() -> None:
    _reset_root_logger()
    from simple_crewai_pair_agent.logging_config import configure_logging

    configure_logging()
    assert len(logging.getLogger().handlers) == 1


def test_log_level_respected() -> None:
    _reset_root_logger()
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
        from simple_crewai_pair_agent.logging_config import configure_logging

        configure_logging()
    assert logging.getLogger().level == logging.DEBUG


def test_idempotent() -> None:
    _reset_root_logger()
    from simple_crewai_pair_agent.logging_config import configure_logging

    configure_logging()
    configure_logging()
    assert len(logging.getLogger().handlers) == 1


def test_invalid_level_falls_back_to_info() -> None:
    _reset_root_logger()
    with patch.dict(os.environ, {"LOG_LEVEL": "NOTAREAL"}):
        from simple_crewai_pair_agent.logging_config import configure_logging

        configure_logging()
    assert logging.getLogger().level == logging.INFO
