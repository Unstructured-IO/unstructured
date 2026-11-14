import io

import docx
import pytest
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from unstructured.documents.elements import ListItem
from unstructured.partition.docx import partition_docx


def linked_document(parts: list[tuple[str, str | None]], style: str | None) -> io.BytesIO:
    document = docx.Document()
    paragraph = document.add_paragraph(style=style)
    for text, url in parts:
        if url is None:
            paragraph.add_run(text)
            continue
        link = OxmlElement("w:hyperlink")
        link.set(qn("r:id"), document.part.relate_to(url, RT.HYPERLINK, is_external=True))
        run = OxmlElement("w:r")
        value = OxmlElement("w:t")
        value.set(qn("xml:space"), "preserve")
        value.text = text
        run.append(value)
        link.append(run)
        paragraph._p.append(link)
    stream = io.BytesIO()
    document.save(stream)
    stream.seek(0)
    return stream


@pytest.mark.parametrize("style", [None, "List Bullet", "List Number"])
@pytest.mark.parametrize("prefix", ["• \t", "•\u00a0", ""])
def test_list_cleanup_keeps_link_offsets_aligned_with_emitted_text(style, prefix):
    parts = [
        (prefix + "Read ", None),
        ("the guide", "https://example.com/guide"),
        (" and ", None),
        ("examples", "https://example.com/examples"),
        (".  ", None),
    ]
    (element,) = partition_docx(file=linked_document(parts, style))

    if prefix or style:
        assert isinstance(element, ListItem)
    assert element.metadata.link_texts == ["the guide", "examples"]
    assert element.metadata.link_urls == [
        "https://example.com/guide",
        "https://example.com/examples",
    ]
    for link in element.metadata.links:
        start = link["start_index"]
        assert start == element.text.index(link["text"])
        assert element.text[start : start + len(link["text"])] == link["text"]


@pytest.mark.parametrize("style", ["List Bullet", "List Number"])
@pytest.mark.parametrize(
    ("parts", "expected_texts"),
    [
        ([("•  Visit", "https://example.com"), (" now", None)], ["Visit"]),
        ([("  Visit  ", "https://example.com")], ["Visit"]),
        ([("• ", "https://example.com/bullet"), ("Visit", "https://example.com")], ["Visit"]),
        ([("Visit", None), ("  ", "https://example.com/space")], None),
    ],
)
def test_list_cleanup_clips_or_removes_links_in_discarded_text(style, parts, expected_texts):
    (element,) = partition_docx(file=linked_document(parts, style))
    assert isinstance(element, ListItem)
    assert element.metadata.link_texts == expected_texts
    assert element.metadata.link_urls == (["https://example.com"] if expected_texts else None)
    if expected_texts is None:
        assert element.metadata.links is None
    else:
        for link in element.metadata.links:
            start = link["start_index"]
            assert start >= 0
            assert element.text[start : start + len(link["text"])] == link["text"]
