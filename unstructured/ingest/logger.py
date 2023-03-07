import logging

logger = logging.getLogger("unstructured.ingest")


def ingest_log_streaming_init(level: int) -> None:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(processName)-10s %(levelname)-8s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
