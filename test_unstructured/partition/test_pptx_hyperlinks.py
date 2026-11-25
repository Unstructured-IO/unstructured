import io

import pptx
import pytest
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Inches

from unstructured.partition.pptx import partition_pptx


def presentation_with_paragraph(title_shape=False):
    presentation = pptx.Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[0 if title_shape else 6])
    shape = (
        slide.shapes.title
        if title_shape
        else slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(2))
    )
    return presentation, shape.text_frame.paragraphs[0]


def add_run(paragraph, text, url=None):
    run = paragraph.add_run()
    run.text = text
    if url:
        run.hyperlink.address = url
    return run


def partition_presentation(presentation, tmp_path, input_kind="file", **kwargs):
    stream = io.BytesIO()
    presentation.save(stream)
    stream.seek(0)
    if input_kind == "filename":
        path = tmp_path / "hyperlinks.pptx"
        path.write_bytes(stream.read())
        return partition_pptx(filename=str(path), **kwargs)
    return partition_pptx(file=stream, **kwargs)


def assert_links(element, expected):
    assert element.metadata.links == expected
    assert element.metadata.link_texts == [link["text"] for link in expected]
    assert element.metadata.link_urls == [link["url"] for link in expected]
    assert element.metadata.link_start_indexes == [link["start_index"] for link in expected]
    for link in expected:
        start = link["start_index"]
        assert element.text[start : start + len(link["text"])] == link["text"]


@pytest.mark.parametrize("title_shape", [False, True])
@pytest.mark.parametrize("input_kind", ["file", "filename"])
def test_pptx_hyperlinks_follow_breaks_fields_unicode_and_repeated_text(
    title_shape, input_kind, tmp_path
):
    presentation, paragraph = presentation_with_paragraph(title_shape)
    add_run(paragraph, "  前言 😀 ")
    paragraph.add_line_break()
    paragraph._p.append(
        parse_xml(
            '<a:fld %s id="{8228817D-8278-4C47-B3AE-927E91BB0B46}" type="slidenum">'
            "<a:t>7</a:t></a:fld>" % nsdecls("a")
        )
    )
    add_run(paragraph, " ")
    first_start = len(paragraph.text)
    add_run(paragraph, "read", "https://example.com/source#section")
    add_run(paragraph, " / ")
    second_start = len(paragraph.text)
    add_run(paragraph, "read", "mailto:reader@example.com?subject=Slides")
    add_run(paragraph, "  ")
    expected_text = paragraph.text.replace("\v", "\n")

    elements = partition_presentation(presentation, tmp_path, input_kind)

    assert len(elements) == 1
    assert elements[0].text == expected_text
    assert elements[0].metadata.page_number == 1
    assert_links(
        elements[0],
        [
            {
                "text": "read",
                "url": "https://example.com/source#section",
                "start_index": first_start,
            },
            {
                "text": "read",
                "url": "mailto:reader@example.com?subject=Slides",
                "start_index": second_start,
            },
        ],
    )


@pytest.mark.parametrize(
    ("kind", "text", "category", "depth"),
    [
        ("title", "Linked title", "Title", 0),
        ("body", "REFERENCE", "Title", 1),
        ("body", "This sentence describes a useful linked resource.", "NarrativeText", 0),
        ("list", "A linked item", "ListItem", 2),
        ("body", "reader@example.com", "EmailAddress", 0),
        ("body", "12345", "UncategorizedText", 0),
    ],
)
def test_hyperlink_metadata_survives_every_paragraph_classification(
    kind, text, category, depth, tmp_path
):
    presentation, paragraph = presentation_with_paragraph(kind == "title")
    if kind == "list":
        paragraph.level = depth
        paragraph._p.get_or_add_pPr().append(parse_xml('<a:buChar %s char="•"/>' % nsdecls("a")))
    add_run(paragraph, text, "https://example.com/reference")

    element = partition_presentation(presentation, tmp_path)[0]

    assert element.category == category
    assert element.metadata.category_depth == depth
    assert_links(
        element, [{"text": text, "url": "https://example.com/reference", "start_index": 0}]
    )


@pytest.mark.parametrize("title_shape", [False, True])
def test_adjacent_formatted_runs_form_one_link_but_plain_text_separates_links(
    title_shape, tmp_path
):
    presentation, paragraph = presentation_with_paragraph(title_shape)
    add_run(paragraph, "See ")
    add_run(paragraph, "cli", "https://example.com")
    add_run(paragraph, "ck", "https://example.com").font.bold = True
    add_run(paragraph, " and ")
    add_run(paragraph, "click", "https://example.com")

    element = partition_presentation(presentation, tmp_path)[0]

    assert_links(
        element,
        [
            {"text": "click", "url": "https://example.com", "start_index": 4},
            {"text": "click", "url": "https://example.com", "start_index": 14},
        ],
    )


@pytest.mark.parametrize(
    "link_kind", ["internal", "missing_relation", "empty_id", "action", "hover"]
)
@pytest.mark.parametrize("external_neighbor", [False, True])
def test_non_external_and_unresolved_links_remain_plain_text(
    link_kind, external_neighbor, tmp_path
):
    presentation, paragraph = presentation_with_paragraph()
    run = add_run(paragraph, "Skip")
    if link_kind == "internal":
        other = presentation.slides.add_slide(presentation.slide_layouts[6])
        rel_id = paragraph.part.relate_to(other.part, RT.SLIDE, is_external=False)
    else:
        rel_id = "rIdMissing" if link_kind == "missing_relation" else ""
    tag = "a:hlinkHover" if link_kind == "hover" else "a:hlinkClick"
    hlink = parse_xml("<%s %s/>" % (tag, nsdecls("a", "r")))
    hlink.set(qn("r:id"), rel_id)
    if link_kind == "action":
        hlink.set("action", "ppaction://hlinkshowjump?jump=nextslide")
    run._r.get_or_add_rPr().append(hlink)
    add_run(paragraph, " ")
    add_run(paragraph, "target", "https://example.com/target" if external_neighbor else None)

    elements = partition_presentation(presentation, tmp_path, include_page_breaks=False)

    assert len(elements) == 1
    assert elements[0].text == "Skip target"
    if external_neighbor:
        assert_links(
            elements[0],
            [{"text": "target", "url": "https://example.com/target", "start_index": 5}],
        )
    else:
        assert elements[0].metadata.links is None
        assert elements[0].metadata.link_urls is None


def test_empty_hyperlinked_runs_do_not_create_empty_links(tmp_path):
    presentation, paragraph = presentation_with_paragraph()
    add_run(paragraph, "", "https://example.com/empty")
    add_run(paragraph, "content", "https://example.com/content")

    element = partition_presentation(presentation, tmp_path)[0]

    assert_links(
        element, [{"text": "content", "url": "https://example.com/content", "start_index": 0}]
    )


def test_unlinked_paragraphs_do_not_acquire_link_metadata(tmp_path):
    presentation, paragraph = presentation_with_paragraph()
    add_run(paragraph, "Ordinary content")

    element = partition_presentation(presentation, tmp_path)[0]

    assert element.text == "Ordinary content"
    assert element.metadata.links is None
    assert element.metadata.link_texts is None
    assert element.metadata.link_urls is None
    assert element.metadata.link_start_indexes is None
