"""`partition()` accepts readable pipes without seeking or closing them."""

import io
import os

from unstructured.partition import auto
from unstructured.partition.auto import partition

TEXT = "Hello world. This is a plain text document."


def _pipe_with_text():
    """Return the read end of a real OS pipe that holds TEXT plus a newline."""
    reader_fd, writer_fd = os.pipe()
    with os.fdopen(writer_fd, "wb") as writer:
        writer.write(TEXT.encode() + b"\n")
    return os.fdopen(reader_fd, "rb")


def test_partition_from_a_real_pipe_with_content_type():
    """partition() reads a whole pipe when content_type is given and leaves it open."""
    with _pipe_with_text() as reader:
        assert not reader.seekable()
        elements = partition(file=reader, content_type="text/plain")
        assert reader.read() == b""
        assert not reader.closed
    assert " ".join(e.text for e in elements) == TEXT


def test_partition_from_a_real_pipe_detects_type_from_metadata_filename():
    """partition() detects a pipe's type from metadata_filename without losing leading bytes."""
    with _pipe_with_text() as reader:
        assert not reader.seekable()
        elements = partition(file=reader, metadata_filename="note.txt")
        assert reader.read() == b""
        assert not reader.closed
    assert " ".join(e.text for e in elements) == TEXT
    assert elements[0].metadata.filetype == "text/plain"


def test_seekable_input_is_passed_through_unchanged(monkeypatch):
    """A seekable file is partitioned in place, not copied into a new buffer."""
    stream = io.BytesIO(TEXT.encode())
    seen = []
    real_detect = auto.detect_filetype

    def spy(*args, **kwargs):
        """Record the file handed to detect_filetype(), then call the real function."""
        seen.append(kwargs["file"])
        return real_detect(*args, **kwargs)

    monkeypatch.setattr(auto, "detect_filetype", spy)
    elements = partition(file=stream, content_type="text/plain")
    assert len(seen) == 1
    assert seen[0] is stream
    assert " ".join(e.text for e in elements) == TEXT
