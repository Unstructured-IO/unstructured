import os
from logging import getLevelName

from unstructured.ingest.logger import make_default_logger

log_level = os.getenv("INGEST_LOG_LEVEL", "INFO")

logger = make_default_logger(level=getLevelName(log_level.upper()))
