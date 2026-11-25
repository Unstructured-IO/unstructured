import io
import os
import sys
from pathlib import Path

import pytest

from unstructured.file_utils.encoding import read_txt_file
from unstructured.partition.common.common import convert_to_bytes


@pytest.mark.parametrize("mode", ["rb", "r"])
@pytest.mark.parametrize("reader", ["bytes", "text"])
def test_named_stream_is_read_even_after_the_working_directory_changes(
    mode: str, reader: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source = tmp_path / "source"
    other = tmp_path / "other"
    source.mkdir()
    other.mkdir()
    original = "café from the original stream"
    (source / "document.txt").write_text(original, encoding="utf-8")
    (other / "document.txt").write_text("replacement document", encoding="utf-8")
    monkeypatch.chdir(source)
    options = {} if mode == "rb" else {"encoding": "utf-8"}
    with open("document.txt", mode, **options) as stream:
        stream.read(2)
        position = stream.tell()
        monkeypatch.chdir(other)

        result = convert_to_bytes(stream) if reader == "bytes" else read_txt_file(file=stream)[1]

        assert result == (original.encode("utf-8") if reader == "bytes" else original)
        assert stream.tell() == position
        assert not stream.closed


@pytest.mark.skipif(sys.platform == "win32", reason="Windows locks paths of these open files")
@pytest.mark.parametrize("mode", ["rb", "r"])
@pytest.mark.parametrize("replace_path", [False, True])
def test_named_stream_survives_unlink_or_path_replacement(
    mode: str, replace_path: bool, tmp_path: Path
):
    path = tmp_path / "document.txt"
    path.write_bytes(b"original stream")
    options = {} if mode == "rb" else {"encoding": "utf-8"}
    with path.open(mode, **options) as stream:
        if replace_path:
            path.rename(tmp_path / "rotated.txt")
            path.write_bytes(b"replacement document")
        else:
            path.unlink()

        assert convert_to_bytes(stream) == b"original stream"
        assert not stream.closed
        assert stream.read() == (b"original stream" if mode == "rb" else "original stream")


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
@pytest.mark.parametrize("read_count", [0, 3, -1])
def test_text_stream_preserves_decoder_position_and_original_bytes(
    encoding: str, read_count: int, tmp_path: Path
):
    text = "café\nsecond line"
    payload = text.encode(encoding)
    path = tmp_path / "encoded.txt"
    path.write_bytes(payload)
    with path.open(encoding=encoding) as stream:
        already_read = stream.read(read_count)
        position = stream.tell()

        assert convert_to_bytes(stream) == payload

        assert stream.tell() == position
        assert stream.read() == text[len(already_read) :]


def test_stream_position_is_restored_when_reading_fails(tmp_path: Path):
    class FailingReader(io.BufferedReader):
        def read(self, *args):
            raise OSError("read failed")

    path = tmp_path / "document.txt"
    path.write_bytes(b"original stream")
    with FailingReader(path.open("rb", buffering=0)) as stream:
        stream.seek(3)

        with pytest.raises(OSError, match="read failed"):
            convert_to_bytes(stream)

        assert stream.tell() == 3
        assert not stream.closed


@pytest.mark.parametrize("text_mode", [False, True])
def test_nonseekable_stream_keeps_its_existing_read_once_behavior(text_mode: bool):
    payload = "café from a pipe".encode("utf-8")
    read_fd, write_fd = os.pipe()
    with os.fdopen(write_fd, "wb") as writer:
        writer.write(payload)
    options = {"encoding": "utf-8"} if text_mode else {}
    with os.fdopen(read_fd, "r" if text_mode else "rb", **options) as stream:
        assert not stream.seekable()
        assert convert_to_bytes(stream) == payload
        assert not stream.closed


def test_bytes_and_memory_streams_keep_their_existing_behavior():
    payload = b"original stream"
    stream = io.BytesIO(payload)
    stream.seek(3)

    assert convert_to_bytes(payload) is payload
    assert convert_to_bytes(stream) == payload
    assert stream.tell() == 3
