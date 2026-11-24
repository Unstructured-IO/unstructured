"""Exercise issue #4466 through the public text, Markdown, and HTML entry points."""

import io
import warnings

import pytest
import requests

from unstructured.file_utils import encoding as encoding_utils
from unstructured.partition.html import partition_html
from unstructured.partition.md import partition_md
from unstructured.partition.text import partition_text

PARTITIONERS = [partition_text, partition_md, partition_html]
SAMPLES = [
    ("会議室予約", "shift_jis"),
    ("café très à Paris", "iso_8859_1"),
    ("髙﨑様と﨑山様が来社されました。", "cp932"),
]


@pytest.mark.parametrize("partition", PARTITIONERS)
@pytest.mark.parametrize(("text", "encoding"), SAMPLES)
@pytest.mark.parametrize("via", ["filename", "stream"])
def test_explicit_encoding_reaches_the_byte_reader(partition, text, encoding, via, tmp_path):
    payload = text.encode(encoding)
    if via == "filename":
        path = tmp_path / "sample.txt"
        path.write_bytes(payload)
        kwargs = {"filename": str(path)}
    else:
        kwargs = {"file": io.BytesIO(payload)}
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        elements = partition(**kwargs, encoding=encoding, languages=[""])
    assert [element.text for element in elements] == [text]


@pytest.mark.parametrize("partition", PARTITIONERS)
def test_automatic_legacy_detection_warns_through_each_partitioner(partition):
    with pytest.warns(UserWarning, match="encoding was inferred"):
        partition(file=io.BytesIO("会議室予約".encode("shift_jis")), languages=[""])


@pytest.mark.parametrize("partition", PARTITIONERS)
def test_warning_as_error_stops_partitioning(partition):
    with warnings.catch_warnings():
        warnings.simplefilter("error", encoding_utils.EncodingDetectionWarning)
        with pytest.raises(encoding_utils.EncodingDetectionWarning):
            partition(file=io.BytesIO("会議室予約".encode("shift_jis")), languages=[""])


@pytest.mark.parametrize("encoding", ["shift_jis", "cp1254"])
def test_markdown_url_honors_an_explicit_encoding(encoding, monkeypatch):
    text = (
        "会議室予約" if encoding == "shift_jis" else "Türkçe bir cümle: şu güzel çiçekler İstanbul."
    )
    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Type"] = "text/markdown"
    response.encoding = "utf-8"
    response._content = text.encode(encoding)
    monkeypatch.setattr("unstructured.partition.md.safe_get", lambda url: response)

    elements = partition_md(url="https://example.test/doc.md", encoding=encoding, languages=[""])

    assert [element.text for element in elements] == [text]


@pytest.mark.parametrize("partition", PARTITIONERS)
def test_already_decoded_text_needs_no_detection(partition):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        elements = partition(text="会議室予約", languages=[""])
    assert [element.text for element in elements] == ["会議室予約"]


def test_markdown_url_does_not_silently_replace_invalid_bytes(monkeypatch):
    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Type"] = "text/markdown"
    response._content = b"\xff"
    monkeypatch.setattr("unstructured.partition.md.safe_get", lambda url: response)

    with pytest.raises(UnicodeDecodeError):
        partition_md(url="https://example.test/doc.md", encoding="utf-8", languages=[""])
