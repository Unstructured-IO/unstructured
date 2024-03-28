import logging

from unstructured.ingest.logger import ingest_log_streaming_init


def log_options(options: dict, verbose=False):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
