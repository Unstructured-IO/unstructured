import logging

from unstructured.logger import DEFAULT_LOG_LEVEL, get_logger


def test_logger_defaults_to_warning(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "")
    logger = get_logger()
    assert logger.level == getattr(logging, DEFAULT_LOG_LEVEL)


def test_logger_reads_from_environment(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    logger = get_logger()
    assert logger.level == 20
