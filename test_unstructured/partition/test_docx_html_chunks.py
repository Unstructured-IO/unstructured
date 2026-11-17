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
    if repeated:
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
