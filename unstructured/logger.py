import logging


def initialize_logger(module_name: str) -> None:
    try:
        from rich.logging import RichHandler as LogHandler
    except ModuleNotFoundError:
        from logging import StreamHandler as LogHandler

    logger = logging.getLogger(module_name)
    logger.setLevel(logging.INFO)
    logger.addHandler(LogHandler())
