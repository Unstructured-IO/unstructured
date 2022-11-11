import logging
import os
import sys

if sys.version_info < (3, 8):
    from typing_extensions import Final
else:
    from typing import Final

DEFAULT_LOG_LEVEL: Final[str] = "WARNING"

logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s")


def get_logger() -> logging.Logger:
    log_level = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    log_level = DEFAULT_LOG_LEVEL if not log_level else log_level
    logger = logging.getLogger(__name__)
    logger.setLevel(level=log_level)
    return logger
