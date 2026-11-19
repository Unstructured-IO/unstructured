import io
import os

import docx
import pytest
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn

from unstructured.partition.common.metadata import get_last_modified_date
from unstructured.partition.docx import partition_docx


def document_with_modified(value: str | None) -> io.BytesIO:
    document = docx.Document()
    document.add_paragraph("This readable document has a recorded modification date.")
    properties = document.core_properties._element
    modified = properties.find(qn("dcterms:modified"))
    if value is None:
        properties.remove(modified)
    elif value == "missing-part":
        for rel_id, rel in list(document.part.package.rels.items()):
            if rel.reltype == RT.CORE_PROPERTIES:
                del document.part.package.rels[rel_id]
    else:
        modified.text = value
    result = io.BytesIO()
    document.save(result)
    result.seek(0)
    return result


@pytest.mark.parametrize("source", ["filename", "stream"])
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2023-09-14T04:12:00Z", "2023-09-14T04:12:00+00:00"),
        ("2023-09-14T04:12:00-07:30", "2023-09-14T11:42:00+00:00"),
        ("2023-09-14T04:12:00+05:30", "2023-09-13T22:42:00+00:00"),
    ],
)
def test_partition_docx_prefers_embedded_modified_date_after_file_copy(
    source, value, expected, tmp_path, monkeypatch
):
    stream = document_with_modified(value)
    if source == "filename":
        path = tmp_path / "copied.docx"
        path.write_bytes(stream.getvalue())
        os.utime(path, (1_700_000_000, 1_700_000_000))
        # Treat the fixture as a regular source document rather than a conversion temporary.
        monkeypatch.setattr("unstructured.partition.docx.is_temp_file_path", lambda _: False)
        elements = partition_docx(filename=str(path))
    else:
        elements = partition_docx(file=stream)
    assert elements[0].metadata.last_modified == expected
    assert elements[0].text == "This readable document has a recorded modification date."


@pytest.mark.parametrize("source", ["filename", "stream"])
@pytest.mark.parametrize(
    "value",
    [
        None,
        "missing-part",
        "invalid date",
        "",
        "9999-12-31T23:59:59-01:00",
        "0001-01-01T00:00:00+01:00",
    ],
)
def test_unavailable_embedded_date_keeps_filesystem_or_none_fallback(
    source, value, tmp_path, monkeypatch
):
    stream = document_with_modified(value)
    if source == "filename":
        path = tmp_path / "undated.docx"
        path.write_bytes(stream.getvalue())
        os.utime(path, (1_700_000_000, 1_700_000_000))
        monkeypatch.setattr("unstructured.partition.docx.is_temp_file_path", lambda _: False)
        expected = get_last_modified_date(str(path))
        elements = partition_docx(filename=str(path))
    else:
        expected = None
        elements = partition_docx(file=stream)
    assert elements[0].metadata.last_modified == expected
    assert elements[0].text


@pytest.mark.parametrize("value", ["2023-09-14T04:12:00Z", None, "missing-part", ""])
def test_explicit_modified_date_still_overrides_document_metadata(value):
    elements = partition_docx(
        file=document_with_modified(value), metadata_last_modified="2020-01-02T03:04:05+00:00"
    )
    assert elements[0].metadata.last_modified == "2020-01-02T03:04:05+00:00"
