import logging

LOGGER_NAME = "unstructured.ingest"


def make_default_logger(level: int = logging.NOTSET) -> logging.Logger:
    """Return a custom logger."""
    logger = logging.getLogger(LOGGER_NAME)
    handler = logging.StreamHandler()
    handler.name = "ingest_log_handler"
    formatter = logging.Formatter("%(asctime)s %(processName)-10s %(levelname)-8s %(message)s")
    handler.setFormatter(formatter)
    # Only want to add the handler once
    if "ingest_log_handler" not in [h.name for h in logger.handlers]:
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
