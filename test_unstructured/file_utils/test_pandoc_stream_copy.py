import io
from pathlib import Path

import pytest

from unstructured.file_utils.file_conversion import convert_file_to_html_text_using_pandoc


class RecordingStream(io.BytesIO):
    def __init__(self, content, short_reads=False):
        super().__init__(content)
        self.read_sizes = []
        self.short_reads = short_reads

    def read(self, size=-1):
        self.read_sizes.append(size)
        if self.short_reads:
            size = min(size, 17) if size >= 0 else 17
        return super().read(size)


@pytest.mark.parametrize("source_format", ["epub", "org", "rst", "rtf"])
@pytest.mark.parametrize("short_reads", [False, True])
def test_pandoc_input_is_copied_in_bounded_reads_without_truncation(
    source_format, short_reads, monkeypatch
):
    payload = bytes(range(256)) * (17 if short_reads else 10000)
    stream = RecordingStream(b"already-consumed" + payload, short_reads=short_reads)
    stream.seek(len(b"already-consumed"))
    temporary_paths = []

    def convert_file_to_text(filename, source_format, target_format):
        temporary_paths.append(Path(filename))
        assert Path(filename).read_bytes() == payload
        assert Path(filename).suffix == "." + source_format
        assert target_format == "html"
        return "<p>converted</p>"

    monkeypatch.setattr(
        "unstructured.file_utils.file_conversion.convert_file_to_text", convert_file_to_text
    )

    result = convert_file_to_html_text_using_pandoc(file=stream, source_format=source_format)

    assert result == "<p>converted</p>"
    assert stream.read_sizes
    assert all(0 < size <= 1024 * 1024 for size in stream.read_sizes)
    assert not stream.closed
    assert not temporary_paths[0].exists()


def test_empty_stream_reaches_converter_and_is_cleaned_up(monkeypatch):
    stream = RecordingStream(b"")
    temporary_paths = []

    def convert_file_to_text(filename, **kwargs):
        temporary_paths.append(Path(filename))
        assert Path(filename).read_bytes() == b""
        return ""

    monkeypatch.setattr(
        "unstructured.file_utils.file_conversion.convert_file_to_text", convert_file_to_text
    )

    assert convert_file_to_html_text_using_pandoc(file=stream, source_format="rst") == ""
    assert not temporary_paths[0].exists()
    assert not stream.closed


def test_copy_failure_removes_partial_file_without_calling_pandoc(monkeypatch, tmp_path):
    class FailingStream:
        def __init__(self):
            self.reads = 0

        def read(self, size=-1):
            self.reads += 1
            if self.reads == 1:
                return b"partial input"
            raise OSError("source stream failed")

    def unexpected_conversion(**kwargs):
        pytest.fail("incomplete input must not reach the converter")

    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
    monkeypatch.setattr(
        "unstructured.file_utils.file_conversion.convert_file_to_text", unexpected_conversion
    )

    with pytest.raises(OSError, match="source stream failed"):
        convert_file_to_html_text_using_pandoc(file=FailingStream(), source_format="rst")

    assert list(tmp_path.iterdir()) == []
