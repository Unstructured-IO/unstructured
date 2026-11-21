import io

import docx
import pytest
from docx.oxml import OxmlElement

from unstructured.partition.docx import partition_docx


def _ruby(base_texts=("漢", "字")):
    ruby = OxmlElement("w:ruby")
    pronunciation = OxmlElement("w:rt")
    ruby.append(pronunciation)
    run = OxmlElement("w:r")
    pronunciation.append(run)
    text = OxmlElement("w:t")
    text.text = "かんじ"
    run.append(text)
    base = OxmlElement("w:rubyBase")
    ruby.append(base)
    for value in base_texts:
        run = OxmlElement("w:r")
        base.append(run)
        text = OxmlElement("w:t")
        text.text = value
        run.append(text)
    return ruby


@pytest.mark.parametrize("location", ["body", "table", "header", "footer", "hyperlink"])
def test_ruby_base_is_preserved_in_document_order_without_phonetic_annotation(location):
    document = docx.Document()
    if location == "table":
        paragraph = document.add_table(rows=1, cols=1).cell(0, 0).paragraphs[0]
    elif location in ("header", "footer"):
        paragraph = getattr(document.sections[0], location).paragraphs[0]
    else:
        paragraph = document.add_paragraph()
    run = paragraph.add_run("Before ")
    run._r.append(_ruby())
    run.add_text(" after")
    if location == "hyperlink":
        link = OxmlElement("w:hyperlink")
        paragraph._p.append(link)
        link.append(run._r)
    file = io.BytesIO()
    document.save(file)
    original = file.getvalue()

    elements = partition_docx(file=file, languages=["eng"])

    assert [element.text for element in elements] == ["Before 漢字 after"]
    assert file.getvalue() == original
    if location == "table":
        assert "漢字" in elements[0].metadata.text_as_html
        assert "かんじ" not in elements[0].metadata.text_as_html


def test_paragraph_containing_only_ruby_is_not_dropped():
    document = docx.Document()
    document.add_paragraph().add_run()._r.append(_ruby())
    file = io.BytesIO()
    document.save(file)

    assert [element.text for element in partition_docx(file=file, languages=["eng"])] == ["漢字"]


def test_ruby_base_preserves_embedded_tabs():
    document = docx.Document()
    run = document.add_paragraph().add_run()
    ruby = _ruby(("漢", "字"))
    ruby.find(docx.oxml.ns.qn("w:rubyBase"))[0].append(OxmlElement("w:tab"))
    run._r.append(ruby)
    file = io.BytesIO()
    document.save(file)

    assert partition_docx(file=file, languages=["eng"])[0].text == "漢\t字"
