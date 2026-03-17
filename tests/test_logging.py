from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from app.core.logging import configure_logging


class LoggingConfigurationTests(unittest.TestCase):
    def test_configure_logging_writes_app_logs_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "app.log"
            logger = configure_logging(log_path)

            logger.warning("test warning written to file")

            for handler in logger.handlers:
                handler.flush()

            self.assertTrue(log_path.exists())
            self.assertIn("test warning written to file", log_path.read_text(encoding="utf-8"))

            for handler in list(logger.handlers):
                if getattr(handler, "_codex_handler_tag", None) == "python-saas-starter":
                    logger.removeHandler(handler)
                    handler.close()
            logger.propagate = True
            logger.setLevel(logging.NOTSET)


if __name__ == "__main__":
    unittest.main()
