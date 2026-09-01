"""Test encoding detection error handling (PR #4071)."""

import os
import pickle
import sys
import tempfile
from unittest.mock import patch

import pytest

from unstructured.errors import UnprocessableEntityError
from unstructured.file_utils.encoding import detect_file_encoding

# Samples from Unstructured-IO/unstructured#4466. charset_normalizer.detect() reports
# johab / windows-1250 for these (outside COMMON_ENCODINGS); both still decode, so the
# UnprocessableEntityError guard never fires and the mojibake becomes the element text.
_OUT_OF_SET_DETECT_CASES = [
    ("会議室予約", "shift_jis"),
    ("café très à Paris", "iso_8859_1"),
    ("Bonjour, ça va très bien. Le café est déjà prêt.", "iso_8859_1"),
]


def test_charset_detection_failure():
    """Test encoding detection failure with memory safety checks."""
    large_data = b"\x80\x81\x82\x83" * 250_000  # 1MB of invalid UTF-8

    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(large_data)
        temp_file_path = f.name

    try:
        detect_result = {"encoding": None, "confidence": None}
        with patch("unstructured.file_utils.encoding.detect", return_value=detect_result):
            with patch("unstructured.file_utils.encoding.COMMON_ENCODINGS", ["utf_8"]):  # Will fail
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


@pytest.mark.parametrize(("text", "encoding"), _OUT_OF_SET_DETECT_CASES)
@pytest.mark.parametrize("via", ["filename", "file"])
def test_detect_file_encoding_recovers_text_when_detect_returns_out_of_set_codec(
    text: str, encoding: str, via: str, tmp_path
):
    payload = text.encode(encoding)
    if via == "filename":
        path = tmp_path / "sample.txt"
        path.write_bytes(payload)
        detected, file_text = detect_file_encoding(filename=str(path))
    else:
        detected, file_text = detect_file_encoding(file=payload)

    assert file_text == text
    assert detected not in {"johab", "windows-1250"}


def test_detect_file_encoding_fallback_reaches_cjk_instead_of_stopping_at_latin1(tmp_path):
    """COMMON_ENCODINGS fallback must not take iso_8859_1 just because it never raises."""
    text = "会議室予約"
    encoding = "shift_jis"
    path = tmp_path / "sample.txt"
    path.write_bytes(text.encode(encoding))
    detect_result = {"encoding": None, "confidence": None}
    with patch("unstructured.file_utils.encoding.detect", return_value=detect_result):
        detected, file_text = detect_file_encoding(filename=str(path))

    assert file_text == text
    assert file_text != text.encode(encoding).decode("iso_8859_1")
    assert detected not in {"iso-8859-1", "latin-1"}
