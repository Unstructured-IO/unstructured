"""Test encoding detection error handling (PR #4071)."""

import codecs
import os
import pickle
import sys
import tempfile
from unittest.mock import patch

import pytest

from test_unstructured.unit_utils import http_response
from unstructured.errors import UnprocessableEntityError
from unstructured.file_utils.encoding import detect_file_encoding, read_response_text


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


# -- read_response_text() ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("content_type", "body", "text"),
    [
        # -- no charset: `requests` assumes ISO-8859-1, but a valid UTF-8 body is read as UTF-8 --
        ("text/html", "Café — 中文 “quote”".encode("utf-8"), "Café — 中文 “quote”"),
        # -- a UTF-8 BOM is dropped, as it is for a file --
        ("text/html", codecs.BOM_UTF8 + "Café".encode("utf-8"), "Café"),
        # -- a body that is not valid UTF-8 keeps the ISO-8859-1 reading --
        ("text/html", "Le café est fermé.".encode("latin-1"), "Le café est fermé."),
        # -- a declared charset is used as before, even when the body is also valid UTF-8 --
        ("text/html; charset=windows-1252", "It’s “cp1252”".encode("cp1252"), "It’s “cp1252”"),
        (
            "text/html; charset=iso-8859-1",
            "Café".encode("utf-8"),
            "Café".encode("utf-8").decode("latin-1"),
        ),
    ],
)
def test_read_response_text_without_an_explicit_encoding(content_type: str, body: bytes, text: str):
    assert read_response_text(http_response(body, content_type)) == text


def test_read_response_text_prefers_an_explicit_encoding_to_the_declared_charset():
    body = "Türkçe bir cümle: şu güzel çiçekler.".encode("cp1254")

    text = read_response_text(http_response(body, "text/html; charset=utf-8"), encoding="cp1254")

    assert text == "Türkçe bir cümle: şu güzel çiçekler."


def test_read_response_text_decodes_an_explicit_encoding_strictly():
    with pytest.raises(UnicodeDecodeError):
        read_response_text(http_response(b"caf\xe9", "text/html"), encoding="utf-8")
