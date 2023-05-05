import pytest

from unstructured.file_utils.filetype import FileType
from unstructured.partition import strategies


def test_validate_strategy_validates():
    # Nothing should raise for a valid strategy
    strategies.validate_strategy("hi_res", FileType.PDF)


def test_validate_strategy_raises_for_bad_filetype():
    with pytest.raises(ValueError):
        strategies.validate_strategy("fast", FileType.JPG)


def test_validate_strategy_raises_for_bad_strategy():
    with pytest.raises(ValueError):
        strategies.validate_strategy("totally_guess_the_text", FileType.JPG)
