"""Native PPTX slide-show visibility and original slide-number preservation."""

from io import BytesIO

import pptx
import pytest
from PIL import Image
from pptx.util import Inches

from unstructured.documents.elements import PageBreak, Text
from unstructured.partition.pptx import PptxPartitionerOptions, partition_pptx


def presentation_bytes(flags, *, pictures=False):
    presentation = pptx.Presentation()
    image = BytesIO()
    Image.new("RGB", (2, 2), "red").save(image, format="PNG")
    for index, flag in enumerate(flags, 1):
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        if flag is not None:
            slide._element.set("show", flag)
        shape = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
        shape.text = f"Slide {index} body"
        slide.notes_slide.notes_text_frame.text = f"Slide {index} speaker notes"
        if pictures:
            image.seek(0)
            slide.shapes.add_picture(image, Inches(1), Inches(3), width=Inches(1))
    output = BytesIO()
    presentation.save(output)
    return output.getvalue()


@pytest.mark.parametrize("hidden_flag", ["0", "false", " false "])
@pytest.mark.parametrize("include_notes", [False, True])
@pytest.mark.parametrize("source", ["file", "filename"])
def test_hidden_slides_can_be_excluded_without_renumbering_retained_slides(
    hidden_flag, include_notes, source, tmp_path
):
    payload = presentation_bytes([hidden_flag, None, hidden_flag, "1", "true", hidden_flag])
    path = tmp_path / "slides.pptx"
    path.write_bytes(payload)
    kwargs = {"filename": str(path)} if source == "filename" else {"file": BytesIO(payload)}

    elements = partition_pptx(
        **kwargs,
        include_hidden_slides=False,
        include_slide_notes=include_notes,
        starting_page_number=7,
        languages=["eng"],
    )

    retained = [element for element in elements if not isinstance(element, PageBreak)]
    expected = []
    for index in (2, 4, 5):
        if include_notes:
            expected.append((f"Slide {index} speaker notes", index + 6))
        expected.append((f"Slide {index} body", index + 6))
    assert [(element.text, element.metadata.page_number) for element in retained] == expected
    assert [
        element.metadata.page_number for element in elements if isinstance(element, PageBreak)
    ] == [8, 10]
    assert not isinstance(elements[0], PageBreak)
    assert not isinstance(elements[-1], PageBreak)
    assert path.read_bytes() == payload


@pytest.mark.parametrize("include_page_breaks", [False, True])
def test_all_hidden_slides_produce_no_content_or_boundaries(include_page_breaks):
    elements = partition_pptx(
        file=BytesIO(presentation_bytes(["0", "false"])),
        include_hidden_slides=False,
        include_page_breaks=include_page_breaks,
        include_slide_notes=True,
        languages=["eng"],
    )

    assert elements == []


def test_original_behavior_includes_hidden_slides_by_default():
    payload = presentation_bytes(["0", None, "false"])

    default = partition_pptx(file=BytesIO(payload), include_slide_notes=True, languages=["eng"])
    explicit = partition_pptx(
        file=BytesIO(payload),
        include_hidden_slides=True,
        include_slide_notes=True,
        languages=["eng"],
    )

    assert [element.to_dict() for element in default] == [element.to_dict() for element in explicit]
    assert len([element for element in default if not isinstance(element, PageBreak)]) == 6


def test_hidden_slides_are_skipped_before_picture_partitioning(monkeypatch):
    visited_pages = []

    class PicturePartitioner:
        @classmethod
        def iter_elements(cls, picture, opts):
            visited_pages.append(opts.page_number)
            yield Text("Picture text", metadata=opts.text_metadata())

    monkeypatch.setattr(PptxPartitionerOptions, "_PicturePartitionerCls", PicturePartitioner)
    elements = partition_pptx(
        file=BytesIO(presentation_bytes([None, "0", None], pictures=True)),
        include_hidden_slides=False,
        include_page_breaks=False,
        languages=["eng"],
    )

    assert visited_pages == [1, 3]
    assert [element.metadata.page_number for element in elements] == [1, 1, 3, 3]
