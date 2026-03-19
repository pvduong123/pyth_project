from __future__ import annotations

import logging
from logging import FileHandler, Formatter, StreamHandler
from pathlib import Path


_LOGGER_NAME = "app"
_HANDLER_TAG = "python-saas-starter"


def configure_logging(log_path: str | Path = "logs/app.log") -> logging.Logger:
    target_path = Path(log_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    app_logger = logging.getLogger(_LOGGER_NAME)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False

    existing_handlers = [
        handler
        for handler in app_logger.handlers
        if getattr(handler, "_codex_handler_tag", None) == _HANDLER_TAG
    ]
    if existing_handlers:
        same_path = any(
            isinstance(handler, FileHandler) and Path(handler.baseFilename) == target_path.resolve()
            for handler in existing_handlers
        )
        if same_path:
            return app_logger
        for handler in existing_handlers:
            app_logger.removeHandler(handler)
            handler.close()

    formatter = Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    stream_handler = StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    stream_handler._codex_handler_tag = _HANDLER_TAG

    file_handler = FileHandler(target_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler._codex_handler_tag = _HANDLER_TAG

    app_logger.addHandler(stream_handler)
    app_logger.addHandler(file_handler)
    return app_logger
