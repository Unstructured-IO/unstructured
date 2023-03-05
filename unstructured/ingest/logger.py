import logging

logger = logging.getLogger("unstructured.ingest")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(processName)-10s %(name)s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def set_ingest_logging_level(level: int) -> None:
    logger.setLevel(level)
