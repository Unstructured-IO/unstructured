"""Preserve run emphasis when Word stores the run inside a hyperlink."""

import io

import docx
import pytest
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from unstructured.partition.docx import partition_docx


def _add_hyperlink(paragraph, text, *, bold=False, italic=False, internal=False):
    hyperlink = OxmlElement("w:hyperlink")
    if internal:
        hyperlink.set(qn("w:anchor"), "topic")
    else:
        relationship = paragraph.part.relate_to(
            "https://example.com/topic", RT.HYPERLINK, is_external=True
        )
        hyperlink.set(qn("r:id"), relationship)
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    hyperlink.append(run._r)
    paragraph._p.append(hyperlink)


def _partition(document):
    stream = io.BytesIO()
    document.save(stream)
    stream.seek(0)
    return partition_docx(file=stream, languages=["eng"])


@pytest.mark.parametrize(
    ("bold", "italic", "tags"),
    [(True, False, ["b"]), (False, True, ["i"]), (True, True, ["b", "i"])],
)
@pytest.mark.parametrize("container", ["paragraph", "table"])
@pytest.mark.parametrize("internal", [False, True])
def test_hyperlink_runs_contribute_emphasis(bold, italic, tags, container, internal):
    document = docx.Document()
    paragraph = (
        document.add_paragraph()
        if container == "paragraph"
        else document.add_table(rows=1, cols=1).cell(0, 0).paragraphs[0]
    )
    paragraph.add_run("Read ")
    _add_hyperlink(paragraph, "the guide", bold=bold, italic=italic, internal=internal)
    paragraph.add_run(" carefully.")

    elements = _partition(document)

    assert len(elements) == 1
    element = elements[0]
    assert element.text == "Read the guide carefully."
    assert element.metadata.emphasized_text_contents == ["the guide"] * len(tags)
    assert element.metadata.emphasized_text_tags == tags
    if container == "paragraph":
        assert element.metadata.link_texts == (None if internal else ["the guide"])
        assert element.metadata.link_urls == (None if internal else ["https://example.com/topic"])


def test_link_and_ordinary_run_emphasis_stays_in_document_order():
    document = docx.Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("Before ").bold = True
    _add_hyperlink(paragraph, "linked", italic=True)
    paragraph.add_run(" middle ").bold = True
    _add_hyperlink(paragraph, "both", bold=True, italic=True)
    paragraph.add_run(" after.").italic = True

    element = _partition(document)[0]

    assert element.metadata.emphasized_text_contents == [
        "Before",
        "linked",
        "middle",
        "both",
        "both",
        "after.",
    ]
    assert element.metadata.emphasized_text_tags == ["b", "i", "b", "b", "i", "i"]


@pytest.mark.parametrize(
    ("bold", "italic", "tags"),
    [(True, False, ["b"]), (False, True, ["i"]), (True, True, ["b", "i"])],
)
def test_ordinary_run_emphasis_is_unchanged(bold, italic, tags):
    document = docx.Document()
    run = document.add_paragraph().add_run(" ordinary text ")
    run.bold = bold
    run.italic = italic

    element = _partition(document)[0]

    assert element.metadata.emphasized_text_contents == ["ordinary text"] * len(tags)
    assert element.metadata.emphasized_text_tags == tags


@pytest.mark.parametrize("link_text", ["plain link", "   "])
def test_unemphasized_or_blank_links_do_not_add_emphasis(link_text):
    document = docx.Document()
    paragraph = document.add_paragraph("Read ")
    _add_hyperlink(paragraph, link_text, bold=link_text.isspace())
    paragraph.add_run(" carefully.")

    element = _partition(document)[0]

    assert element.metadata.emphasized_text_contents is None
    assert element.metadata.emphasized_text_tags is None
