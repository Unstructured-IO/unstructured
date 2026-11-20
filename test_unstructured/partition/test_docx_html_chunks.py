from io import BytesIO

import pytest
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from unstructured.documents.elements import Table, Title
from unstructured.partition.docx import partition_docx
from unstructured.staging.base import elements_from_dicts, elements_to_dicts

HTML = """<html><body><h1>Imported section</h1>
<p>Detailed café information with <b>strong evidence</b> and
<a href="https://example.com/source">source material</a>.</p>
<table><tr><th>Region</th><th>Count</th></tr><tr><td>West</td><td>7</td></tr></table>
</body></html>"""


def document_with_chunk(
    *,
    encoding="utf-8",
    content_type="text/html",
    sectionless=False,
    kind="internal",
    repeated=False,
    html=None,
    page_break=False,
    deleted=False,
):
    document = Document()
    before = document.add_paragraph("Before imported content")
    if page_break:
        before.runs[0]._r.append(OxmlElement("w:lastRenderedPageBreak"))
    if kind == "external":
        relation_id = document.part.relate_to(
            "https://example.invalid/chunk.html", RT.A_F_CHUNK, is_external=True
        )
    else:
        part = Part(
            PackURI("/word/chunks/import.html"),
            content_type,
            HTML.encode(encoding) if html is None else html,
            document.part.package,
        )
        relation_id = document.part.relate_to(
            part, RT.HYPERLINK if kind == "wrong-type" else RT.A_F_CHUNK
        )
    chunk = OxmlElement("w:altChunk")
    chunk.set(qn("r:id"), "missing" if kind == "missing" else relation_id)
    if deleted:
        wrapper = OxmlElement("w:del")
        wrapper.append(chunk)
        chunk = wrapper
    document.element.body.insert(len(document.element.body) - 1, chunk)
    document.add_paragraph("After imported content")
    for _ in range(repeated):
        repeated_chunk = OxmlElement("w:altChunk")
        repeated_chunk.set(qn("r:id"), relation_id)
        document.element.body.insert(len(document.element.body) - 1, repeated_chunk)
    if sectionless:
        document.element.body.remove(document.element.body.sectPr)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


@pytest.mark.parametrize("source", ["file", "filename"])
@pytest.mark.parametrize("sectionless", [False, True])
@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_internal_html_imports_preserve_document_order_and_content(
    tmp_path, source, sectionless, encoding
):
    payload = document_with_chunk(sectionless=sectionless, encoding=encoding)
    path = tmp_path / "imported.docx"
    path.write_bytes(payload)
    file = BytesIO(payload)
    kwargs = {"file": file} if source == "file" else {"filename": str(path)}

    elements = partition_docx(**kwargs, metadata_filename="report.docx", languages=["eng"])

    assert len(elements) == 5
    assert elements[0].text == "Before imported content"
    assert elements[-1].text == "After imported content"
    title, paragraph, table = elements[1:4]
    assert isinstance(title, Title)
    assert title.text == "Imported section"
    assert "café information" in paragraph.text
    assert paragraph.metadata.link_urls == ["https://example.com/source"]
    assert paragraph.metadata.emphasized_text_contents == ["strong evidence"]
    assert isinstance(table, Table)
    assert "West" in table.text
    assert "<table>" in table.metadata.text_as_html
    assert all(element.metadata.filename == "report.docx" for element in elements)
    assert all(element.metadata.page_number is None for element in elements)
    assert all(
        element.metadata.filetype.endswith("wordprocessingml.document") for element in elements
    )
    assert elements_from_dicts(elements_to_dicts(elements)) == elements
    assert path.read_bytes() == payload
    assert file.getvalue() == payload


@pytest.mark.parametrize("infer_table_structure", [False, True])
def test_chunk_tables_follow_docx_table_structure_setting(infer_table_structure):
    elements = partition_docx(
        file=BytesIO(document_with_chunk()),
        infer_table_structure=infer_table_structure,
        languages=["eng"],
    )
    table = next(element for element in elements if isinstance(element, Table))

    assert (table.metadata.text_as_html is not None) is infer_table_structure
    assert "Region" in table.text


def test_html_imports_can_be_disabled():
    elements = partition_docx(
        file=BytesIO(document_with_chunk()), include_alt_chunks=False, languages=["eng"]
    )

    assert [element.text for element in elements] == [
        "Before imported content",
        "After imported content",
    ]


@pytest.mark.parametrize("kind", ["external", "missing", "wrong-type", "unsupported"])
def test_unreadable_imports_do_not_fetch_urls_or_discard_main_document(kind, monkeypatch):
    def reject_network(*args, **kwargs):
        pytest.fail("embedded document extraction must not make a request")

    monkeypatch.setattr("requests.sessions.Session.request", reject_network)
    payload = document_with_chunk(
        kind=kind, content_type="application/rtf" if kind == "unsupported" else "text/html"
    )

    elements = partition_docx(file=BytesIO(payload), languages=["eng"])

    assert [element.text for element in elements] == [
        "Before imported content",
        "After imported content",
    ]


def test_repeated_references_are_inserted_at_each_anchor_with_independent_hierarchy():
    elements = partition_docx(file=BytesIO(document_with_chunk(repeated=True)), languages=["eng"])

    assert [element.text for element in elements if isinstance(element, Title)].count(
        "Imported section"
    ) == 2
    first_title, second_title = [
        element for element in elements if element.text == "Imported section"
    ]
    paragraphs = [element for element in elements if "café information" in element.text]
    assert [element.metadata.parent_id for element in paragraphs] == [
        first_title.id,
        second_title.id,
    ]


def test_xhtml_parts_are_read_as_html_content():
    elements = partition_docx(
        file=BytesIO(document_with_chunk(content_type="application/xhtml+xml")), languages=["eng"]
    )

    assert any(element.text == "Imported section" for element in elements)


@pytest.mark.parametrize("html", [b"", b" \n\t"])
def test_empty_imports_leave_the_surrounding_body_readable(html):
    elements = partition_docx(file=BytesIO(document_with_chunk(html=html)), languages=["eng"])

    assert [element.text for element in elements] == [
        "Before imported content",
        "After imported content",
    ]


def test_deleted_import_anchors_are_not_extracted():
    elements = partition_docx(file=BytesIO(document_with_chunk(deleted=True)), languages=["eng"])

    assert [element.text for element in elements] == [
        "Before imported content",
        "After imported content",
    ]


def test_imported_elements_use_the_page_number_at_their_anchor():
    elements = partition_docx(
        file=BytesIO(document_with_chunk(page_break=True)),
        starting_page_number=9,
        languages=["eng"],
    )

    imported = [
        element
        for element in elements
        if element.text not in ("", "Before imported content", "After imported content")
    ]
    assert len(imported) == 3
    assert all(element.metadata.page_number == 10 for element in imported)
    assert elements[0].metadata.page_number == 9


def test_imports_keep_body_content_before_inside_and_after_main():
    payload = document_with_chunk(
        html=b"<body><p>Before main</p><main><p>Inside main</p></main><p>After main</p></body>"
    )

    elements = partition_docx(file=BytesIO(payload), languages=["eng"])

    assert [element.text for element in elements] == [
        "Before imported content",
        "Before main",
        "Inside main",
        "After main",
        "After imported content",
    ]


def test_imported_tables_keep_spans_and_rows_fully_covered_by_a_span():
    payload = document_with_chunk(
        html=(
            b'<table><thead><tr><th colspan="2" onclick="alert(1)">Region</th></tr></thead>'
            b'<tbody><tr><th rowspan="2">West</th><td>7</td></tr><tr><td>8</td></tr>'
            b'<tr><td rowspan="2" colspan="2">Shared</td></tr><tr></tr></tbody></table>'
        )
    )

    elements = partition_docx(file=BytesIO(payload), languages=["eng"])
    table = next(element for element in elements if isinstance(element, Table))

    assert table.metadata.text_as_html == (
        '<table><thead><tr><th colspan="2">Region</th></tr></thead>'
        '<tbody><tr><th rowspan="2">West</th><td>7</td></tr><tr><td>8</td></tr>'
        '<tr><td rowspan="2" colspan="2">Shared</td></tr><tr></tr></tbody></table>'
    )


def test_invalid_import_encoding_keeps_surrounding_document_content(caplog):
    payload = document_with_chunk(html=b"\xff\xfe\x00")

    elements = partition_docx(file=BytesIO(payload), languages=["eng"])

    assert [element.text for element in elements] == [
        "Before imported content",
        "After imported content",
    ]
    assert "Skipping unreadable DOCX HTML import" in caplog.text


@pytest.mark.parametrize("html", [b"", b"<style>" + b"a{color:red}" * 10_000 + b"</style>"])
def test_repeated_empty_imports_are_parsed_once_per_part(html, mocker):
    from unstructured.partition.html.partition import _HtmlPartitioner

    parse = mocker.spy(_HtmlPartitioner, "iter_elements")
    payload = document_with_chunk(html=html, repeated=20)

    elements = partition_docx(file=BytesIO(payload), languages=["eng"])

    assert [element.text for element in elements] == [
        "Before imported content",
        "After imported content",
    ]
    assert parse.call_count == 1


@pytest.mark.parametrize("unique_element_ids", [False, True])
def test_repeated_imports_have_independent_elements_metadata_and_anchor_pages(unique_element_ids):
    document = Document(BytesIO(document_with_chunk(repeated=True, page_break=True)))
    document.paragraphs[-1].runs[0]._r.append(OxmlElement("w:lastRenderedPageBreak"))
    output = BytesIO()
    document.save(output)

    elements = partition_docx(
        file=BytesIO(output.getvalue()),
        languages=["eng"],
        starting_page_number=9,
        unique_element_ids=unique_element_ids,
    )
    paragraphs = [element for element in elements if "café information" in element.text]
    first, second = paragraphs

    assert first is not second
    assert first.metadata is not second.metadata
    assert first.id != second.id
    assert [element.metadata.page_number for element in paragraphs] == [10, 11]
    first.metadata.link_urls.append("https://example.com/only-first")
    assert second.metadata.link_urls == ["https://example.com/source"]
