import io

import pptx
import pytest
from pptx.util import Inches

from unstructured.partition.pptx import partition_pptx


@pytest.mark.parametrize("title", [False, True])
def test_partition_preserves_run_and_paragraph_emphasis(title):
    presentation = pptx.Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[0 if title else 6])
    shape = (
        slide.shapes.title
        if title
        else slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(2))
    )
    paragraph = shape.text_frame.paragraphs[0]
    paragraph.font.bold = True
    for text, bold, italic in [
        (" Inherited ", None, None),
        ("plain ", False, None),
        ("both ", True, True),
        ("italic ", False, True),
        ("  ", True, True),
    ]:
        run = paragraph.add_run()
        run.text = text
        run.font.bold = bold
        run.font.italic = italic
    file = io.BytesIO()
    presentation.save(file)

    elements = partition_pptx(file=file, languages=["eng"])

    element = next(e for e in elements if "Inherited" in e.text)
    assert element.metadata.emphasized_text_contents == ["Inherited", "both", "both", "italic"]
    assert element.metadata.emphasized_text_tags == ["b", "b", "i", "i"]
    assert element.text == " Inherited plain both italic   "
    assert element.metadata.page_number == 1


def test_unformatted_presentation_omits_emphasis_metadata():
    presentation = pptx.Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    shape = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(2))
    shape.text = "This paragraph has no explicit emphasis."
    file = io.BytesIO()
    presentation.save(file)

    element = partition_pptx(file=file, languages=["eng"])[0]

    assert element.metadata.emphasized_text_contents is None
    assert element.metadata.emphasized_text_tags is None
