"""Test encoding detection error handling (PR #4071)."""

import os
import pickle
import sys
import tempfile
from unittest.mock import patch

import pytest

from unstructured.errors import UnprocessableEntityError
from unstructured.file_utils.encoding import detect_file_encoding


def test_charset_detection_failure():
    """Test encoding detection failure with memory safety checks."""
    large_data = bytes(range(256)) * 4096  # 1MiB of deterministic binary data

    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(large_data)
        temp_file_path = f.name

    try:
        detect_result = {"encoding": None, "confidence": None}
        with patch("unstructured.file_utils.encoding.detect", return_value=detect_result):
            with pytest.raises(UnprocessableEntityError) as exc_info:
                detect_file_encoding(filename=temp_file_path)

            exception = exc_info.value

            assert "Unable to determine file encoding" in str(exception)

            # Ensure no .object attribute that would store file content (prevents memory bloat)
            # See: https://docs.python.org/3/library/exceptions.html#UnicodeError.object
            assert not hasattr(exception, "object")

            # Exception should be lightweight regardless of file size
            exception_memory = sys.getsizeof(exception)
            serialized_size = len(pickle.dumps(exception))

            assert exception_memory < 10_000  # Small in-memory footprint
            assert serialized_size < 10_000  # Small serialization footprint
    finally:
        os.unlink(temp_file_path)


def test_decode_failure():
    """Test decode failure with memory safety checks."""
    # Invalid UTF-16: BOM followed by odd number of bytes
    invalid_utf16 = b"\xff\xfe" + b"A\x00B\x00" + b"\x00"

    detect_result = {"encoding": "utf-16", "confidence": 0.95}
    with patch("unstructured.file_utils.encoding.detect", return_value=detect_result):
        with pytest.raises(UnprocessableEntityError) as exc_info:
            detect_file_encoding(file=invalid_utf16)

        exception = exc_info.value

        assert "detected 'utf-16' but decode failed" in str(exception)

        # Ensure no .object attribute that would store file content (prevents memory bloat)
        # See: https://docs.python.org/3/library/exceptions.html#UnicodeError.object
        assert not hasattr(exception, "object")

        # Exception should be lightweight
        exception_memory = sys.getsizeof(exception)
        serialized_size = len(pickle.dumps(exception))

        assert exception_memory < 10_000  # Small in-memory footprint
        assert serialized_size < 10_000  # Small serialization footprint
