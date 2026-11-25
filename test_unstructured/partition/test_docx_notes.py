"""Native DOCX note parts, references, and part-local relationships."""

from io import BytesIO

import docx
import pytest
from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from unstructured.partition.docx import partition_docx
from unstructured.staging.base import elements_from_dicts


def add_reference(paragraph, kind, note_id):
    run = paragraph.add_run()
    run._r.append(parse_xml(f'<w:{kind}Reference {nsdecls("w")} w:id="{note_id}"/>'))


def add_notes(document, kind):
    plural = f"{kind}s"
    content_type = CT.WML_FOOTNOTES if kind == "footnote" else CT.WML_ENDNOTES
    relationship = RT.FOOTNOTES if kind == "footnote" else RT.ENDNOTES
    xml = (
        f"<w:{plural} {nsdecls('w', 'r')}>"
        f'<w:{kind} w:id="-1" w:type="separator"><w:p><w:r>'
        f"<w:t>Separator must not leak</w:t></w:r></w:p></w:{kind}>"
        f'<w:{kind} w:id="0" w:type="continuationSeparator"><w:p><w:r>'
        f"<w:t>Continuation must not leak</w:t></w:r></w:p></w:{kind}>"
        f'<w:{kind} w:id="99"><w:p><w:r>'
        f"<w:t>Unreferenced note must not leak</w:t></w:r></w:p></w:{kind}>"
        f'<w:{kind} w:id="2"><w:p><w:r><w:t>Second {kind}.</w:t></w:r></w:p>'
        '<w:tbl><w:tblPr/><w:tblGrid><w:gridCol w:w="3000"/><w:gridCol w:w="3000"/>'
        "</w:tblGrid><w:tr><w:tc><w:p><w:r><w:t>Evidence</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>Confirmed</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"
        f"</w:{kind}>"
        f'<w:{kind} w:id="1"><w:p><w:r><w:rPr><w:b/></w:rPr><w:{kind}Ref/>'
        f"<w:t>First {kind}.</w:t></w:r></w:p>"
        '<w:p><w:hyperlink r:id="rId1"><w:r><w:t>Reference link</w:t></w:r>'
        f"</w:hyperlink></w:p></w:{kind}>"
        f"</w:{plural}>"
    )
    part = Part(PackURI(f"/word/{plural}.xml"), content_type, xml.encode(), document.part.package)
    part.relate_to(f"https://example.test/{kind}/source", RT.HYPERLINK, is_external=True)
    document.part.relate_to(part, relationship)


def note_document(kind, *, table_reference=False, sectionless=False, blank_anchor=False):
    document = docx.Document()
    first = document.add_paragraph(
        "" if blank_anchor else "An initial paragraph with supporting evidence."
    )
    add_reference(first, kind, 1)
    second = (
        document.add_table(rows=1, cols=1).cell(0, 0).paragraphs[0]
        if table_reference
        else document.add_paragraph()
    )
    second.add_run("A second paragraph describes the result.")
    add_reference(second, kind, 2)
    repeated = document.add_paragraph("A repeated reference should not duplicate its note.")
    add_reference(repeated, kind, 1)
    # Corrupt/missing note references should not drop surrounding document text.
    add_reference(repeated, kind, 404)
    add_reference(repeated, kind, -1)
    add_notes(document, kind)
    if sectionless:
        document._element.body.remove(document._element.body.sectPr)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


@pytest.mark.parametrize("kind", ["footnote", "endnote"])
@pytest.mark.parametrize("source", ["file", "filename"])
def test_referenced_notes_preserve_content_structure_and_relationships(kind, source, tmp_path):
    payload = note_document(kind)
    path = tmp_path / "notes.docx"
    path.write_bytes(payload)
    kwargs = {"filename": str(path)} if source == "filename" else {"file": BytesIO(payload)}

    elements = partition_docx(**kwargs, languages=["eng"])

    assert [element.text for element in elements] == [
        "An initial paragraph with supporting evidence.",
        f"First {kind}.",
        "Reference link",
        "A second paragraph describes the result.",
        f"Second {kind}.",
        "Evidence Confirmed",
        "A repeated reference should not duplicate its note.",
    ]
    assert [elements[i].category for i in (1, 2, 4, 5)] == ["Footer", "Footer", "Footer", "Table"]
    assert elements[1].metadata.emphasized_text_contents == [f"First {kind}."]
    assert elements[2].metadata.link_urls == [f"https://example.test/{kind}/source"]
    assert elements[5].metadata.text_as_html is not None
    for child, parent in ((1, 0), (2, 0), (4, 3), (5, 3)):
        assert elements[child].metadata.parent_id == elements[parent].id
        assert elements[child].metadata.header_footer_type == kind
    assert [
        element.to_dict() for element in elements_from_dicts([e.to_dict() for e in elements])
    ] == [element.to_dict() for element in elements]
    assert path.read_bytes() == payload


@pytest.mark.parametrize("kind", ["footnote", "endnote"])
def test_note_references_inside_tables_follow_the_containing_table(kind):
    elements = partition_docx(
        file=BytesIO(note_document(kind, table_reference=True)), languages=["eng"]
    )

    assert elements[3].category == "Table"
    assert elements[4].text == f"Second {kind}."
    assert elements[4].metadata.parent_id == elements[3].id
    assert elements[5].metadata.parent_id == elements[3].id


@pytest.mark.parametrize("kind", ["footnote", "endnote"])
def test_notes_are_available_in_sectionless_documents(kind):
    elements = partition_docx(
        file=BytesIO(note_document(kind, sectionless=True)), languages=["eng"]
    )

    assert elements[1].text == f"First {kind}."
    assert elements[1].metadata.parent_id == elements[0].id


@pytest.mark.parametrize("kind", ["footnote", "endnote"])
def test_reference_only_paragraph_does_not_drop_the_note(kind):
    elements = partition_docx(
        file=BytesIO(note_document(kind, blank_anchor=True)), languages=["eng"]
    )

    assert elements[0].text == f"First {kind}."
    assert elements[0].metadata.parent_id is None


@pytest.mark.parametrize("kind", ["footnote", "endnote"])
def test_notes_can_be_disabled_without_changing_body_text(kind):
    elements = partition_docx(
        file=BytesIO(note_document(kind)), include_notes=False, languages=["eng"]
    )

    assert [element.text for element in elements] == [
        "An initial paragraph with supporting evidence.",
        "A second paragraph describes the result.",
        "A repeated reference should not duplicate its note.",
    ]


def test_footnotes_and_endnotes_with_the_same_id_are_distinct():
    document = docx.Document()
    paragraph = document.add_paragraph("This paragraph has two independent notes.")
    for kind in ("footnote", "endnote"):
        add_reference(paragraph, kind, 1)
        add_notes(document, kind)
    output = BytesIO()
    document.save(output)

    elements = partition_docx(file=BytesIO(output.getvalue()), languages=["eng"])

    assert [element.text for element in elements] == [
        "This paragraph has two independent notes.",
        "First footnote.",
        "Reference link",
        "First endnote.",
        "Reference link",
    ]
    assert {element.metadata.parent_id for element in elements[1:]} == {elements[0].id}


@pytest.mark.parametrize("kind", ["footnote", "endnote"])
@pytest.mark.parametrize("revision", ["del", "moveFrom"])
def test_deleted_references_do_not_reintroduce_discarded_notes(kind, revision):
    document = docx.Document()
    paragraph = document.add_paragraph("Only the surviving body text is visible.")
    paragraph._p.append(
        parse_xml(
            f'<w:{revision} {nsdecls("w")} w:id="1" w:author="Editor">'
            f'<w:r><w:{kind}Reference w:id="1"/></w:r></w:{revision}>'
        )
    )
    add_notes(document, kind)
    output = BytesIO()
    document.save(output)

    elements = partition_docx(file=BytesIO(output.getvalue()), languages=["eng"])

    assert [element.text for element in elements] == ["Only the surviving body text is visible."]


@pytest.mark.parametrize("kind", ["footnote", "endnote"])
def test_malformed_optional_note_part_keeps_body_text(kind, caplog):
    document = docx.Document()
    paragraph = document.add_paragraph("The body remains readable.")
    add_reference(paragraph, kind, 1)
    content_type = CT.WML_FOOTNOTES if kind == "footnote" else CT.WML_ENDNOTES
    relationship = RT.FOOTNOTES if kind == "footnote" else RT.ENDNOTES
    part = Part(PackURI(f"/word/{kind}s.xml"), content_type, b"<broken", document.part.package)
    document.part.relate_to(part, relationship)
    output = BytesIO()
    document.save(output)

    elements = partition_docx(file=BytesIO(output.getvalue()), languages=["eng"])

    assert [element.text for element in elements] == ["The body remains readable."]
    assert f"Skipping malformed DOCX {kind} part" in caplog.text


@pytest.mark.parametrize("kind", ["footnote", "endnote"])
def test_note_tables_respect_infer_table_structure(kind):
    elements = partition_docx(
        file=BytesIO(note_document(kind)), infer_table_structure=False, languages=["eng"]
    )

    assert elements[5].text == "Evidence Confirmed"
    assert elements[5].category == "Table"
    assert elements[5].metadata.text_as_html is None
