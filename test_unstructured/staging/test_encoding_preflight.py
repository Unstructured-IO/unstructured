from functools import partial

import pytest

from unstructured.documents.elements import Text
from unstructured.staging.base import (
    create_file_from_elements,
    elements_to_json,
    elements_to_md,
    elements_to_ndjson,
    elements_to_text,
)

EXPORTERS = [
    elements_to_md,
    elements_to_text,
    elements_to_json,
    elements_to_ndjson,
    partial(create_file_from_elements, output_format="text"),
    partial(create_file_from_elements, output_format="markdown"),
    partial(create_file_from_elements, output_format="html"),
]


@pytest.mark.parametrize("export", EXPORTERS)
def test_unknown_encoding_does_not_truncate_an_existing_export(tmp_path, export):
    destination = tmp_path / "document.txt"
    destination.write_bytes(b"Existing document must survive")

    with pytest.raises(LookupError):
        export([Text("New document")], filename=str(destination), encoding="not-a-real-encoding")

    assert destination.read_bytes() == b"Existing document must survive"


@pytest.mark.parametrize("export", [EXPORTERS[i] for i in (0, 1, 4, 5, 6)])
@pytest.mark.parametrize("already_exists", [False, True])
def test_unencodable_text_does_not_replace_or_create_an_export(tmp_path, export, already_exists):
    destination = tmp_path / "document.txt"
    if already_exists:
        destination.write_bytes(b"Previous document")
    # Put the failing code point beyond the first preflight block.
    elements = [Text("A" * 70000 + "文")]

    with pytest.raises(UnicodeEncodeError):
        export(elements, filename=str(destination), encoding="ascii")

    if already_exists:
        assert destination.read_bytes() == b"Previous document"
    else:
        assert not destination.exists()


@pytest.mark.parametrize("export", EXPORTERS)
@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "iso2022_jp"])
def test_successful_encoding_preserves_export_content_and_codec_state(tmp_path, export, encoding):
    destination = tmp_path / "document.txt"

    elements = [Text("行一\n行二")]
    expected = export(elements, encoding=encoding)
    result = export(elements, filename=str(destination), encoding=encoding)

    assert destination.read_text(encoding=encoding) == expected
    if result is not None:
        assert result == expected
