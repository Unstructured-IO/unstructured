import logging

import pytest

from unstructured_inference import logger


@pytest.mark.parametrize("level", range(50))
def test_translate_log_level(level):
    level_name = logging.getLevelName(level)
    if level_name in ["WARNING", "INFO", "DEBUG", "NOTSET", "WARN"]:
        expected = 4
    elif level_name in ["ERROR", "CRITICAL"]:
        expected = 3
    else:
        expected = 0
    assert logger.translate_log_level(level) == expected
