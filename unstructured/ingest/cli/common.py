import logging

from unstructured.ingest.logger import ingest_log_streaming_init, logger


def options_redactions(options: dict) -> dict:
    # handle any logic needed to redact not already caught by the logging filter
    options = options.copy()
    if "uri" in options and options["uri"].startswith("mongodb"):
        from unstructured.ingest.connector.mongodb import redact

        options["uri"] = redact(options["uri"])
    return options


def log_options(options: dict, verbose=False):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    logger.debug(f"options: {options_redactions(options)}")
