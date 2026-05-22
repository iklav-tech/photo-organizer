from __future__ import annotations

import logging

from photo_organizer.logging_config import configure_logging


def test_configure_logging_adds_single_stdout_handler_and_sets_level(monkeypatch) -> None:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    try:
        root_logger.handlers.clear()

        configure_logging("DEBUG")
        assert len(root_logger.handlers) == 1
        assert root_logger.level == logging.DEBUG
        assert root_logger.handlers[0].formatter is not None
        assert root_logger.handlers[0].formatter._fmt == "[%(levelname)s] %(message)s"

        configure_logging("ERROR")
        assert len(root_logger.handlers) == 1
        assert root_logger.level == logging.ERROR

        configure_logging("not-a-real-level")
        assert root_logger.level == logging.INFO
    finally:
        root_logger.handlers.clear()
        root_logger.handlers.extend(original_handlers)
        root_logger.setLevel(original_level)
