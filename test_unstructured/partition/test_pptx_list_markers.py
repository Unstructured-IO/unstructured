import io

import pptx
import pytest
from PIL import Image
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Inches

from unstructured.documents.elements import ListItem, Title
from unstructured.partition.pptx import partition_pptx


def make_paragraph(title_shape):
    presentation = pptx.Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[0 if title_shape else 6])
    shape = (
        slide.shapes.title
        if title_shape
        else slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(2))
    )
    return presentation, shape.text_frame.paragraphs[0]


def partition_serialized(presentation, **kwargs):
    stream = io.BytesIO()
    presentation.save(stream)
    stream.seek(0)
    return partition_pptx(file=stream, **kwargs)


@pytest.mark.parametrize("title_shape", [False, True])
@pytest.mark.parametrize("level", [0, 2])
@pytest.mark.parametrize("number_style", ["arabicPeriod", "alphaLcParenR", "romanUcPeriod"])
def test_automatic_numbering_preserves_list_classification_and_nesting(
    title_shape, level, number_style
):
    presentation, paragraph = make_paragraph(title_shape)
    paragraph.text = "REFERENCE"
    paragraph.level = level
    paragraph._p.get_or_add_pPr().append(
        parse_xml('<a:buAutoNum %s type="%s" startAt="4"/>' % (nsdecls("a"), number_style))
    )

    elements = partition_serialized(presentation)

    assert len(elements) == 1
    assert isinstance(elements[0], ListItem)
    assert elements[0].text == "REFERENCE"
    assert elements[0].metadata.category_depth == level
    assert elements[0].metadata.page_number == 1


@pytest.mark.parametrize("title_shape", [False, True])
@pytest.mark.parametrize("level", [0, 3])
def test_picture_bullets_are_list_items(title_shape, level):
    presentation, paragraph = make_paragraph(title_shape)
    paragraph.text = "REFERENCE"
    paragraph.level = level
    image = io.BytesIO()
    Image.new("RGB", (2, 2), "black").save(image, format="PNG")
    image.seek(0)
    _, rel_id = paragraph.part.get_or_add_image_part(image)
    bullet = parse_xml("<a:buBlip %s><a:blip/></a:buBlip>" % nsdecls("a", "r"))
    bullet[0].set(qn("r:embed"), rel_id)
    paragraph._p.get_or_add_pPr().append(bullet)

    elements = partition_serialized(presentation)

    assert len(elements) == 1
    assert isinstance(elements[0], ListItem)
    assert elements[0].text == "REFERENCE"
    assert elements[0].metadata.category_depth == level


@pytest.mark.parametrize("title_shape", [False, True])
def test_existing_character_bullets_keep_their_classification(title_shape):
    presentation, paragraph = make_paragraph(title_shape)
    paragraph.text = "REFERENCE"
    paragraph.level = 1
    paragraph._p.get_or_add_pPr().append(parse_xml('<a:buChar %s char="•"/>' % nsdecls("a")))

    element = partition_serialized(presentation)[0]

    assert isinstance(element, ListItem)
    assert element.text == "REFERENCE"
    assert element.metadata.category_depth == 1


@pytest.mark.parametrize("title_shape", [False, True])
@pytest.mark.parametrize("properties", ["<a:buNone/>", '<a:buFont typeface="Arial"/>'])
def test_no_bullet_and_bullet_formatting_alone_do_not_create_list_items(title_shape, properties):
    presentation, paragraph = make_paragraph(title_shape)
    paragraph.text = "REFERENCE"
    paragraph._p.append(parse_xml("<a:pPr %s>%s</a:pPr>" % (nsdecls("a"), properties)))

    element = partition_serialized(presentation)[0]

    assert isinstance(element, Title)
    assert element.text == "REFERENCE"
    assert element.metadata.category_depth == (0 if title_shape else 1)


@pytest.mark.parametrize("title_shape", [False, True])
def test_blank_numbered_paragraph_does_not_emit_an_empty_item_or_change_the_next_level(title_shape):
    presentation, blank = make_paragraph(title_shape)
    blank.text = "  "
    blank._p.get_or_add_pPr().append(
        parse_xml('<a:buAutoNum %s type="arabicPeriod"/>' % nsdecls("a"))
    )
    paragraph = blank._parent.add_paragraph()
    paragraph.text = "REFERENCE"
    paragraph.level = 2
    paragraph._p.get_or_add_pPr().append(
        parse_xml('<a:buAutoNum %s type="arabicPeriod"/>' % nsdecls("a"))
    )

    elements = partition_serialized(presentation)

    assert len(elements) == 1
    assert isinstance(elements[0], ListItem)
    assert elements[0].metadata.category_depth == 2


@pytest.mark.parametrize("title_shape", [False, True])
def test_numbered_items_do_not_create_spurious_title_chunk_boundaries(title_shape):
    presentation, first = make_paragraph(title_shape)
    text_frame = first._parent
    for index, text in enumerate(["STEP ONE", "STEP TWO", "STEP THREE"]):
        paragraph = first if index == 0 else text_frame.add_paragraph()
        paragraph.text = text
        paragraph._p.get_or_add_pPr().append(
            parse_xml('<a:buAutoNum %s type="arabicPeriod"/>' % nsdecls("a"))
        )

    chunks = partition_serialized(
        presentation,
        chunking_strategy="by_title",
        combine_text_under_n_chars=0,
        max_characters=1000,
    )

    assert len(chunks) == 1
    assert chunks[0].text == "STEP ONE\n\nSTEP TWO\n\nSTEP THREE"
    assert all(isinstance(item, ListItem) for item in chunks[0].metadata.orig_elements)
