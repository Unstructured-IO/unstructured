import io

import docx
import pytest
from docx.oxml import OxmlElement

from unstructured.partition.docx import partition_docx


@pytest.mark.parametrize("location", ["body", "table", "header", "footer", "hyperlink"])
@pytest.mark.parametrize("double", [False, True])
def test_opt_in_omits_explicitly_struck_text(location, double):
    document = docx.Document()
    if location == "table":
        paragraph = document.add_table(rows=1, cols=1).cell(0, 0).paragraphs[0]
    elif location in ("header", "footer"):
        paragraph = getattr(document.sections[0], location).paragraphs[0]
    else:
        paragraph = document.add_paragraph()
    paragraph.add_run("Keep ")
    run = paragraph.add_run("obsolete ")
    run.bold = True
    if double:
        run.font.double_strike = True
    else:
        run.font.strike = True
    if location == "hyperlink":
        hyperlink = OxmlElement("w:hyperlink")
        paragraph._p.append(hyperlink)
        hyperlink.append(run._r)
    paragraph.add_run("current")
    file = io.BytesIO()
    document.save(file)
    original = file.getvalue()

    elements = partition_docx(file=file, skip_strikethrough=True, languages=["eng"])

    assert [e.text for e in elements] == ["Keep current"]
    assert all("obsolete" not in (e.metadata.text_as_html or "") for e in elements)
    assert all(not e.metadata.emphasized_text_contents for e in elements)
    assert file.getvalue() == original


@pytest.mark.parametrize("skip", [False, True])
def test_explicitly_disabled_strike_is_kept(skip):
    document = docx.Document()
    run = document.add_paragraph().add_run("Current content")
    run.font.strike = False
    run.font.double_strike = False
    file = io.BytesIO()
    document.save(file)

    assert partition_docx(file=file, skip_strikethrough=skip, languages=["eng"])[0].text == (
        "Current content"
    )


def test_default_preserves_struck_content():
    document = docx.Document()
    document.add_paragraph().add_run("Still present").font.strike = True
    file = io.BytesIO()
    document.save(file)

    assert partition_docx(file=file, languages=["eng"])[0].text == "Still present"
