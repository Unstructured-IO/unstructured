import os
import tempfile

import numpy as np
import pytest
from PIL import Image
from unstructured_inference.constants import IsExtracted
from unstructured_inference.constants import Source as InferenceSource
from unstructured_inference.inference.elements import (
    EmbeddedTextRegion,
    Rectangle,
    TextRegion,
    TextRegions,
)
from unstructured_inference.inference.layout import DocumentLayout, LayoutElement, PageLayout
from unstructured_inference.inference.layoutelement import LayoutElements

from test_unstructured.unit_utils import example_doc_path
from unstructured.partition.auto import partition
from unstructured.partition.pdf import process_file_with_core_pdf
from unstructured.partition.pdf_image.layout_processing import (
    _rotate_bboxes,
    _validate_bbox,
    aggregate_embedded_text_by_block,
    bboxes1_is_almost_subregion_of_bboxes2,
    boxes_self_iou,
    clean_pdf_extracted_inner_elements,
    remove_duplicate_elements,
)
from unstructured.partition.utils.constants import Source

# A set of elements with core-pdf elements inside tables
deletable_elements_inside_table = [
    LayoutElement(
        bbox=Rectangle(0, 0, 100, 100),
        text="Table with inner elements",
        type="Table",
    ),
    LayoutElement(bbox=Rectangle(50, 50, 70, 70), text="text1", source=Source.CORE_PDF),
    LayoutElement(bbox=Rectangle(70, 70, 80, 80), text="text2", source=Source.CORE_PDF),
]

# A set of elements without core-pdf elements inside
# tables (no elements with source=Source.CORE_PDF)
no_deletable_elements_inside_table = [
    LayoutElement(
        bbox=Rectangle(0, 0, 100, 100),
        text="Table with inner elements",
        type="Table",
        source=InferenceSource.YOLOX,
    ),
    LayoutElement(bbox=Rectangle(50, 50, 70, 70), text="text1", source=InferenceSource.YOLOX),
    LayoutElement(bbox=Rectangle(70, 70, 80, 80), text="text2", source=InferenceSource.YOLOX),
]
# A set of elements with core-pdf elements inside tables and other
# elements with source=Source.CORE_PDF
# Note: some elements with source=Source.CORE_PDF are not inside tables
mix_elements_inside_table = [
    LayoutElement(
        bbox=Rectangle(0, 0, 100, 100),
        text="Table1 with inner elements",
        type="Table",
        source=InferenceSource.YOLOX,
    ),
    LayoutElement(bbox=Rectangle(50, 50, 70, 70), text="Inside table1"),
    LayoutElement(bbox=Rectangle(70, 70, 80, 80), text="Inside table1", source=Source.CORE_PDF),
    LayoutElement(
        bbox=Rectangle(150, 150, 170, 170),
        text="Outside tables",
        source=Source.CORE_PDF,
    ),
    LayoutElement(
        bbox=Rectangle(180, 180, 200, 200),
        text="Outside tables",
        source=Source.CORE_PDF,
    ),
    LayoutElement(
        bbox=Rectangle(0, 500, 100, 700),
        text="Table2 with inner elements",
        type="Table",
        source=InferenceSource.YOLOX,
    ),
    LayoutElement(bbox=Rectangle(0, 510, 50, 600), text="Inside table2", source=Source.CORE_PDF),
    LayoutElement(bbox=Rectangle(0, 550, 70, 650), text="Inside table2", source=Source.CORE_PDF),
]


def test_rotate_bboxes_matches_pil_rotation_directions():
    """_rotate_bboxes mirrors PIL.Image.rotate(angle, expand=True) (counter-clockwise)."""
    W, H = 100.0, 200.0  # portrait display-frame canvas
    coords = np.array([[10.0, 20.0, 30.0, 60.0]])

    # 0 / 360 are no-ops
    assert np.array_equal(_rotate_bboxes(coords, 0, W, H), coords)
    assert np.array_equal(_rotate_bboxes(coords, 360, W, H), coords)

    # 90 CCW (expand): x' = y, y' = W - x
    r90 = _rotate_bboxes(coords, 90, W, H)
    assert np.allclose(r90, [[20.0, W - 30.0, 60.0, W - 10.0]])
    # 180
    r180 = _rotate_bboxes(coords, 180, W, H)
    assert np.allclose(r180, [[W - 30.0, H - 60.0, W - 10.0, H - 20.0]])
    # 270 CCW
    assert np.allclose(_rotate_bboxes(coords, 270, W, H), [[H - 60.0, 10.0, H - 20.0, 30.0]])

    # rotating 90 then 270 (about the post-rotation H x W canvas) restores the original box
    assert np.allclose(_rotate_bboxes(r90, 270, H, W), coords)

    # outputs remain valid bboxes (x1 < x2, y1 < y2)
    for angle in (90, 180, 270):
        r = _rotate_bboxes(coords, angle, W, H)
        assert r[0, 0] < r[0, 2]
        assert r[0, 1] < r[0, 3]


@pytest.mark.parametrize(
    ("bbox", "is_valid"),
    [
        ([0, 1, 0, 1], False),
        ([0, 1, 1, 2], True),
        ([0, 1, 1, None], False),
        ([0, 1, 1, np.nan], False),
        ([0, 1, -1, 0], False),
        ([0, 1, -1, 2], False),
    ],
)
def test_valid_bbox(bbox, is_valid):
    assert _validate_bbox(bbox) is is_valid


@pytest.mark.parametrize(
    ("elements", "expected_document_length"),
    [
        (deletable_elements_inside_table, 1),
        (no_deletable_elements_inside_table, 3),
        (mix_elements_inside_table, 5),
    ],
)
def test_clean_pdf_extracted_inner_elements(elements, expected_document_length):
    # create a sample document with extracted PDF elements inside tables
    page = PageLayout(number=1, image=Image.new("1", (1, 1)))
    page.elements_array = LayoutElements.from_list(elements)
    document_with_table = DocumentLayout(pages=[page])
    document = document_with_table

    # call the function to clean the extracted PDF inner elements
    cleaned_doc = clean_pdf_extracted_inner_elements(document)

    # verify extracted PDF elements inside table bounding boxes are removed
    assert len(cleaned_doc.pages[0].elements_array) == expected_document_length


def test_clean_pdf_extracted_inner_elements_keeps_text_inside_non_table_blocks():
    elements = [
        LayoutElement(
            bbox=Rectangle(0, 0, 100, 100),
            text="Title block",
            type="Title",
            source=InferenceSource.YOLOX,
        ),
        LayoutElement(
            bbox=Rectangle(10, 10, 40, 40),
            text="Inside title",
            source=Source.CORE_PDF,
        ),
        LayoutElement(
            bbox=Rectangle(200, 200, 300, 300),
            text="Table block",
            type="Table",
            source=InferenceSource.YOLOX,
        ),
        LayoutElement(
            bbox=Rectangle(210, 210, 240, 240),
            text="Inside table",
            source=Source.CORE_PDF,
        ),
        LayoutElement(
            bbox=Rectangle(400, 400, 440, 440),
            text="Outside table",
            source=Source.CORE_PDF,
        ),
    ]
    page = PageLayout(number=1, image=Image.new("1", (1, 1)))
    page.elements_array = LayoutElements.from_list(elements)
    document = DocumentLayout(pages=[page])

    cleaned_doc = clean_pdf_extracted_inner_elements(document)

    assert list(cleaned_doc.pages[0].elements_array.texts) == [
        "Title block",
        "Inside title",
        "Table block",
        "Outside table",
    ]


elements_with_duplicate_images = [
    LayoutElement(
        bbox=Rectangle(0, 0, 100, 100),
        text="Image1",
        type="Image",
        source=Source.CORE_PDF,
    ),
    LayoutElement(
        bbox=Rectangle(10, 10, 110, 110), text="Image1", type="Image", source=Source.CORE_PDF
    ),
    LayoutElement(bbox=Rectangle(150, 150, 170, 170), text="Title1", type="Title"),
]

elements_without_duplicate_images = [
    LayoutElement(
        bbox=Rectangle(0, 0, 100, 100),
        text="Sample image",
        type="Image",
        source=Source.CORE_PDF,
    ),
    LayoutElement(
        bbox=Rectangle(10, 10, 110, 110),
        text="Sample image with similar bbox",
        type="Image",
        source=Source.CORE_PDF,
    ),
    LayoutElement(
        bbox=Rectangle(200, 200, 250, 250),
        text="Sample image",
        type="Image",
        source=Source.CORE_PDF,
    ),
    LayoutElement(bbox=Rectangle(150, 150, 170, 170), text="Title1", type="Title"),
]


def test_aggregate_by_block():
    expected = "Inside region1 Inside region2"
    embedded_regions = TextRegions.from_list(
        [
            TextRegion.from_coords(0, 0, 300, 20, "Inside region1"),
            TextRegion.from_coords(0, 20, 300, 80, None),
            TextRegion.from_coords(0, 80, 200, 300, "Inside region2"),
            TextRegion.from_coords(250, 250, 350, 350, "Outside region"),
        ]
    )
    embedded_regions.is_extracted_array = np.array([IsExtracted.TRUE] * 4)
    target_region = TextRegions.from_list([TextRegion.from_coords(0, 0, 300, 300)])

    text, extracted = aggregate_embedded_text_by_block(target_region, embedded_regions)
    assert text == expected
    assert extracted.value == "true"


def test_aggregate_only_partially_fill_target():
    expected = "Inside region1"
    embedded_regions = TextRegions.from_list(
        [
            TextRegion.from_coords(0, 0, 20, 20, "Inside region1"),
        ]
    )
    embedded_regions.is_extracted_array = np.array([IsExtracted.TRUE])
    target_region = TextRegions.from_list([TextRegion.from_coords(0, 0, 300, 300)])

    text, extracted = aggregate_embedded_text_by_block(target_region, embedded_regions)
    assert text == expected
    assert extracted.value == "partial"


def test_aggregate_overlapping_regions_do_not_overstate_target_coverage():
    embedded_regions = TextRegions.from_list(
        [
            TextRegion.from_coords(0, 0, 20, 100, "Inside region1"),
            TextRegion.from_coords(0, 0, 20, 100, "Inside region2"),
        ]
    )
    embedded_regions.is_extracted_array = np.array([IsExtracted.TRUE, IsExtracted.TRUE])
    target_region = TextRegions.from_list([TextRegion.from_coords(0, 0, 100, 100)])

    text, extracted = aggregate_embedded_text_by_block(target_region, embedded_regions)
    assert text == "Inside region1 Inside region2"
    assert extracted is IsExtracted.PARTIAL


def test_aggregate_not_filling_target():
    embedded_regions = TextRegions.from_list(
        [
            TextRegion.from_coords(300, 0, 400, 20, "outside"),
        ]
    )
    embedded_regions.is_extracted_array = np.array([IsExtracted.TRUE])
    target_region = TextRegions.from_list([TextRegion.from_coords(0, 0, 300, 300)])

    text, extracted = aggregate_embedded_text_by_block(target_region, embedded_regions)
    assert text == ""
    assert extracted.value == "false"


@pytest.mark.parametrize(
    ("coords1", "coords2", "expected"),
    [
        (
            [[0, 0, 10, 10], [10, 0, 20, 10], [10, 10, 20, 20]],
            [[0, 0, 10, 10], [0, 0, 12, 12]],
            [[True, True], [False, False], [False, False]],
        ),
        (
            [[0, 0, 10, 10], [10, 0, 20, 10], [10, 10, 20, 20]],
            [[0, 0, 10, 10], [10, 10, 22, 22], [0, 0, 5, 5]],
            [[True, False, False], [False, False, False], [False, True, False]],
        ),
        (
            [[0, 0, 10, 10], [10, 10, 10, 10]],
            [[0, 0, 10, 10], [10, 10, 22, 22], [0, 0, 5, 5]],
            [[True, False, False], [True, True, False]],
        ),
    ],
)
def test_bboxes1_is_almost_subregion_of_bboxes2(coords1, coords2, expected):
    bboxes1 = [Rectangle(*row) for row in coords1]
    bboxes2 = [Rectangle(*row) for row in coords2]
    np.testing.assert_array_equal(
        bboxes1_is_almost_subregion_of_bboxes2(bboxes1, bboxes2), expected
    )


@pytest.mark.parametrize(
    ("coords", "threshold", "expected"),
    [
        (
            [[0, 0, 10, 10], [2, 2, 12, 12], [10, 10, 20, 20]],
            0.5,
            [[True, True, False], [True, True, False], [False, False, True]],
        ),
        (
            [[0, 0, 10, 10], [2, 2, 12, 12], [10, 10, 20, 20]],
            0.9,
            [[True, False, False], [False, True, False], [False, False, True]],
        ),
        (
            [[0, 0, 10, 10], [10, 10, 10, 10]],
            0.5,
            [[True, False], [False, True]],
        ),
    ],
)
def test_boxes_self_iou(coords, threshold, expected):
    bboxes = [Rectangle(*row) for row in coords]
    np.testing.assert_array_equal(boxes_self_iou(bboxes, threshold), expected)


def test_remove_duplicate_elements():
    sample_elements = TextRegions.from_list(
        [
            EmbeddedTextRegion(bbox=Rectangle(0, 0, 10, 10), text="Text 1"),
            EmbeddedTextRegion(bbox=Rectangle(0, 0, 10, 10), text="Text 2"),
            EmbeddedTextRegion(bbox=Rectangle(20, 20, 30, 30), text="Text 3"),
        ]
    )

    result = remove_duplicate_elements(sample_elements)

    # Check that duplicates were removed and only 2 unique elements remain
    assert len(result) == 2
    assert result.texts.tolist() == ["Text 2", "Text 3"]
    assert result.element_coords.tolist() == [[0, 0, 10, 10], [20, 20, 30, 30]]


def test_remove_duplicate_elements_dense_page_is_not_decimated():
    """Pages with more than ~2000 elements are chunked internally; the dedup mask for each
    chunk must be offset by the chunk's global index. Otherwise rows in later chunks match
    themselves and are wrongly dropped, decimating dense pages."""
    # 2500 unique, non-overlapping boxes on a 50x50 grid (zero IoU between any two)
    unique = [
        EmbeddedTextRegion(
            bbox=Rectangle((i % 50) * 20, (i // 50) * 20, (i % 50) * 20 + 10, (i // 50) * 20 + 10),
            text=f"Text {i}",
        )
        for i in range(2500)
    ]
    # one exact duplicate of the first box, appended last so the pair spans two chunks
    duplicate = EmbeddedTextRegion(bbox=Rectangle(0, 0, 10, 10), text="Text 0 dup")
    sample_elements = TextRegions.from_list([*unique, duplicate])

    result = remove_duplicate_elements(sample_elements)

    # only the single cross-chunk duplicate pair collapses; every unique box is kept
    assert len(result) == 2500
    # the later element of the duplicate pair is the one retained
    assert "Text 0 dup" in result.texts.tolist()
    assert "Text 0" not in result.texts.tolist()


def test_process_file_with_core_pdf():
    layout, links = process_file_with_core_pdf(
        example_doc_path("pdf/layout-parser-paper-fast.pdf"),
    )
    assert len(layout) == 2
    assert layout[0].texts[0] == "arXiv:2103.15348v2 [cs.CV] 21 Jun 2021"
    assert [[link["url"] for link in page_links] for page_links in links] == [
        ["cite.harley2015evaluation"],
        [
            "cite.xu2019layoutlm",
            "cite.zhong2019publaynet",
            "cite.oliveira2018dhsegment",
            "cite.prasad2020cascadetabnet",
            "cite.baek2019character",
            "cite.tensorflow2015-whitepaper",
            "cite.paszke2019pytorch",
            "cite.gardner2018allennlp",
            "section.1.3",
            "section.1.4",
            "cite.gardner2018allennlp",
            "cite.wolf2019huggingface",
            "cite.wu2019detectron2",
        ],
    ]


def test_process_file_with_core_pdf_is_extracted_array():
    layout, _ = process_file_with_core_pdf(example_doc_path("pdf/layout-parser-paper-fast.pdf"))
    text_flags = [
        is_extracted
        for text, is_extracted in zip(layout[0].texts, layout[0].is_extracted_array)
        if text is not None
    ]
    assert all(is_extracted is IsExtracted.TRUE for is_extracted in text_flags)
    assert all(is_extracted is IsExtracted.TRUE for is_extracted in layout[1].is_extracted_array)


def test_process_file_hidden_ocr_text():
    """Test processing a PDF that contains hidden OCR text layer."""
    layout, _ = process_file_with_core_pdf(example_doc_path("pdf/pdf-with-ocr-text.pdf"))
    text_flags = [
        is_extracted
        for text, is_extracted in zip(layout[0].texts, layout[0].is_extracted_array)
        if text is not None
    ]
    assert all(is_extracted is IsExtracted.TRUE for is_extracted in text_flags)


def test_process_file_recovers_figure_overlay_text():
    """Text inside a Form XObject (LTFigure overlay) is recovered, not dropped.

    Regression test: such text is real, embedded text in a form XObject that older extraction used
    to drop. The fixture has "Printed Name:" in the main content stream and "Jane Doe" inside a
    form XObject.
    """
    layout, _ = process_file_with_core_pdf(example_doc_path("pdf/figure-overlay-text.pdf"))
    texts = " ".join(str(t) for page in layout for t in page.texts if t)
    assert "Printed Name:" in texts  # main content stream
    assert "Jane Doe" in texts  # figure-overlay text (dropped before the fix)


# A synthetic AcroForm: filled text fields whose values live only in widget annotations
# (the page content stream is empty), plus one empty field that must be skipped.
SYNTHETIC_FORM_FIELDS = [
    ("name", "Jane Doe", (40, 700, 300, 720)),
    ("date of birth", "1990-01-01", (40, 650, 300, 670)),
    ("address", "123 Main Street", (40, 600, 300, 620)),
    ("phone", "", (40, 550, 300, 570)),  # empty -> should be skipped
]


def _build_synthetic_form_pdf(path: str) -> None:
    """Write a 1-page PDF whose only text lives in AcroForm text-field (/Tx) widgets.

    The page content stream is empty, so normal content-stream text extraction yields nothing; the
    values are reachable only through the widget annotations in ``page.annots``.
    """
    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        DictionaryObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    page = writer.pages[0]

    refs = []
    for field_name, value, rect in SYNTHETIC_FORM_FIELDS:
        widget = DictionaryObject()
        widget[NameObject("/Type")] = NameObject("/Annot")
        widget[NameObject("/Subtype")] = NameObject("/Widget")
        widget[NameObject("/FT")] = NameObject("/Tx")
        widget[NameObject("/T")] = TextStringObject(field_name)
        widget[NameObject("/V")] = TextStringObject(value)
        widget[NameObject("/Rect")] = ArrayObject([NumberObject(c) for c in rect])
        refs.append(writer._add_object(widget))

    page[NameObject("/Annots")] = ArrayObject(refs)
    acro_form = DictionaryObject()
    acro_form[NameObject("/Fields")] = ArrayObject(refs)
    writer._root_object[NameObject("/AcroForm")] = writer._add_object(acro_form)

    with open(path, "wb") as f:
        writer.write(f)


def test_process_file_with_core_pdf_recovers_form_field_text():
    """The extracted (hi_res) layer includes AcroForm field values as text regions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = os.path.join(tmp_dir, "form.pdf")
        _build_synthetic_form_pdf(pdf_path)
        layout, _ = process_file_with_core_pdf(pdf_path)

    texts = [str(t) for t in layout[0].texts if t]
    assert "Jane Doe" in texts
    assert "1990-01-01" in texts
    assert "123 Main Street" in texts
    # Widget-sourced regions are marked as extracted text.
    assert IsExtracted.TRUE in list(layout[0].is_extracted_array)


def test_partition_pdf_fast_recovers_form_field_text():
    """End-to-end: the fast strategy emits elements for filled form fields."""
    from unstructured.partition.pdf import partition_pdf

    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = os.path.join(tmp_dir, "form.pdf")
        _build_synthetic_form_pdf(pdf_path)
        elements = partition_pdf(filename=pdf_path, strategy="fast")

    blob = "\n".join(el.text for el in elements)
    assert "Jane Doe" in blob
    assert "1990-01-01" in blob
    assert "123 Main Street" in blob


def test_partition_uses_core_pdf_extraction():
    elements = partition(
        filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
    )
    assert [element.text for element in elements[:12]] == [
        "arXiv:2103.15348v2 [cs.CV] 21 Jun 2021",
        "Layout Parser: A Uniﬁed Toolkit for Deep",
        "Learning Based Document Image Analysis",
        "Zejiang Shen¹ (a0), Ruochen Zhang², Melissa Dell³, Benjamin Charles Germain",
        "Lee⁴, Jacob Carlson³, and Weining Li⁵",
        "1 Allen Institute for AI",
        "shannons@allenai.org",
        "2 Brown University",
        "ruochen zhang@brown.edu",
        "3 Harvard University",
        "{melissadell,jacob carlson}@fas.harvard.edu",
        "4 University of Washington",
    ]
