import io

import docx
import pptx
import pytest
from PIL import Image as PILImage
from pptx.util import Inches

from unstructured.documents.elements import Image
from unstructured.partition.docx import DocxPartitionerOptions, partition_docx
from unstructured.partition.pptx import PptxPartitionerOptions, partition_pptx


def _document(kind, title, description):
    image = io.BytesIO()
    PILImage.new("RGB", (10, 10), "white").save(image, "PNG")
    image.seek(0)
    if kind == "docx":
        document = docx.Document()
        properties = document.add_picture(image)._inline.docPr
    else:
        document = pptx.Presentation()
        slide = document.slides.add_slide(document.slide_layouts[6])
        picture = slide.shapes.add_picture(image, Inches(1), Inches(1))
        properties = picture._element.xpath("./p:nvPicPr/p:cNvPr")[0]
    properties.set("title", title)
    properties.set("descr", description)
    file = io.BytesIO()
    document.save(file)
    return file


@pytest.mark.parametrize("kind", ["docx", "pptx"])
@pytest.mark.parametrize(
    ("title", "description", "expected"),
    [
        ("", "Revenue increased by 20%.", "Revenue increased by 20%."),
        ("Revenue chart", "", "Revenue chart"),
        ("Revenue chart", "Revenue increased by 20%.", "Revenue chart\nRevenue increased by 20%."),
        (" Same description ", "Same description", "Same description"),
    ],
)
def test_authored_picture_alt_text_can_be_extracted_without_ocr(kind, title, description, expected):
    file = _document(kind, title, description)
    original = file.getvalue()
    partition = partition_docx if kind == "docx" else partition_pptx

    elements = partition(
        file=file, include_image_alt_text=True, starting_page_number=5, languages=["eng"]
    )

    assert len(elements) == 1
    assert isinstance(elements[0], Image)
    assert elements[0].text == expected
    assert elements[0].metadata.page_number == (5 if kind == "pptx" else None)
    assert file.getvalue() == original


@pytest.mark.parametrize("kind", ["docx", "pptx"])
def test_picture_without_authored_alt_text_does_not_emit_filename_as_content(kind):
    partition = partition_docx if kind == "docx" else partition_pptx

    assert (
        partition(file=_document(kind, " ", "\n"), include_image_alt_text=True, languages=["eng"])
        == []
    )


@pytest.mark.parametrize("kind", ["docx", "pptx"])
def test_picture_alt_text_is_opt_in(kind):
    partition = partition_docx if kind == "docx" else partition_pptx

    assert partition(file=_document(kind, "Chart", "Description"), languages=["eng"]) == []


@pytest.mark.parametrize("kind", ["docx", "pptx"])
def test_registered_picture_partitioner_keeps_control_without_duplicate_alt_text(kind, monkeypatch):
    class CustomPicturePartitioner:
        @classmethod
        def iter_elements(cls, picture, opts):
            yield Image("Custom result")

    options = DocxPartitionerOptions if kind == "docx" else PptxPartitionerOptions
    partition = partition_docx if kind == "docx" else partition_pptx
    monkeypatch.setattr(options, "_PicturePartitionerCls", CustomPicturePartitioner)

    elements = partition(
        file=_document(kind, "Chart", "Description"),
        include_image_alt_text=True,
        languages=["eng"],
    )

    assert [element.text for element in elements] == ["Custom result"]
