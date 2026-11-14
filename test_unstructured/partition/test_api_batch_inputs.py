import io
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from unstructured.partition import api


@pytest.fixture
def post(monkeypatch: pytest.MonkeyPatch) -> Mock:
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps([[], []]).encode()
    post = Mock(return_value=response)
    monkeypatch.setattr(api.requests, "post", post)
    return post


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "both",
        "empty_filenames",
        "empty_files",
        "empty_paths_with_streams",
        "paths_with_empty_streams",
    ],
)
def test_batch_requires_one_nonempty_document_source(case: str, tmp_path: Path, post: Mock):
    filename = tmp_path / "document.txt"
    filename.write_text("Document content", encoding="utf-8")
    stream = io.BytesIO(b"Stream content")
    kwargs = {
        "missing": {},
        "both": {"filenames": [str(filename)], "files": [stream]},
        "empty_filenames": {"filenames": []},
        "empty_files": {"files": []},
        "empty_paths_with_streams": {"filenames": [], "files": [stream]},
        "paths_with_empty_streams": {"filenames": [str(filename)], "files": []},
    }[case]

    with pytest.raises(ValueError):
        api.partition_multiple_via_api(**kwargs)

    post.assert_not_called()
    assert not stream.closed
    assert stream.tell() == 0


@pytest.mark.parametrize("source", ["filenames", "files"])
def test_empty_content_types_is_rejected_before_opening_or_uploading(
    source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, post: Mock
):
    filename = tmp_path / "document.txt"
    filename.write_text("Document content", encoding="utf-8")
    stream = io.BytesIO(b"Stream content")
    kwargs = (
        {"filenames": [str(filename)]}
        if source == "filenames"
        else {"files": [stream], "metadata_filenames": ["document.txt"]}
    )
    opened = Mock(wraps=open)
    monkeypatch.setattr(api, "open", opened, raising=False)

    with pytest.raises(ValueError, match="content_types.*same length"):
        api.partition_multiple_via_api(content_types=[], **kwargs)

    opened.assert_not_called()
    post.assert_not_called()
    assert not stream.closed
    assert stream.tell() == 0


@pytest.mark.parametrize("source", ["filenames", "files"])
def test_valid_batch_keeps_document_order_and_content_types(
    source: str, tmp_path: Path, post: Mock
):
    paths = [tmp_path / "first.txt", tmp_path / "second.html"]
    for path in paths:
        path.write_text(path.stem, encoding="utf-8")
    streams = tuple(io.BytesIO(path.read_bytes()) for path in paths)
    names = [str(path) for path in paths]
    kwargs = (
        {"filenames": names}
        if source == "filenames"
        else {"files": streams, "metadata_filenames": names}
    )

    assert api.partition_multiple_via_api(content_types=["text/plain", "text/html"], **kwargs) == [
        [],
        [],
    ]

    post.assert_called_once()
    uploads = post.call_args.kwargs["files"]
    assert [(upload[1][0], upload[1][2]) for upload in uploads] == [
        (names[0], "text/plain"),
        (names[1], "text/html"),
    ]
    if source == "filenames":
        assert all(upload[1][1].closed for upload in uploads)
    else:
        assert tuple(upload[1][1] for upload in uploads) == streams
        assert all(not stream.closed and stream.tell() == 0 for stream in streams)
