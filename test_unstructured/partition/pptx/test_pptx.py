# pyright: reportPrivateUsage=false

"""Test suite for `unstructured.partition.pptx` module."""

import os
import pathlib
from typing import Iterator, Sequence, cast

import pptx
import pytest
from pptx.util import Inches
from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    ListItem,
    NarrativeText,
    PageBreak,
    Text,
    Title,
)
from unstructured.partition.pptx import _PptxPartitioner, partition_pptx

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "..", "..", "example-docs")

EXPECTED_PPTX_OUTPUT = [
    Title(text="Adding a Bullet Slide"),
    ListItem(text="Find the bullet slide layout"),
    ListItem(text="Use _TextFrame.text for first bullet"),
    ListItem(text="Use _TextFrame.add_paragraph() for subsequent bullets"),
    NarrativeText(text="Here is a lot of text!"),
    NarrativeText(text="Here is some text in a text box!"),
]


def get_test_file_path(filename: str) -> str:
    return str(pathlib.Path(__file__).parent / "test_files" / filename)


# == DescribePptxPartitionerSourceFileBehaviors ==================================================


def test_partition_pptx_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    elements = partition_pptx(filename=filename)
    assert elements == EXPECTED_PPTX_OUTPUT
    for element in elements:
        assert element.metadata.filename == "fake-power-point.pptx"


def test_partition_pptx_from_filename_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    elements = partition_pptx(filename=filename, metadata_filename="test")
    assert elements == EXPECTED_PPTX_OUTPUT
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_pptx_with_spooled_file():
    """The `partition_pptx() function can handle a `SpooledTemporaryFile.

    Including one that does not have its read-pointer set to the start.
    """
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    from tempfile import SpooledTemporaryFile

    with open(filename, "rb") as test_file:
        spooled_temp_file = SpooledTemporaryFile()
        spooled_temp_file.write(test_file.read())
        elements = partition_pptx(file=spooled_temp_file)
        assert elements == EXPECTED_PPTX_OUTPUT
        for element in elements:
            assert element.metadata.filename is None


def test_partition_pptx_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    with open(filename, "rb") as f:
        elements = partition_pptx(file=f)
    assert elements == EXPECTED_PPTX_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_pptx_from_file_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    with open(filename, "rb") as f:
        elements = partition_pptx(file=f, metadata_filename="test")
    assert elements == EXPECTED_PPTX_OUTPUT
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_pptx_raises_with_both_specified():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    with open(filename, "rb") as f, pytest.raises(ValueError):
        partition_pptx(filename=filename, file=f)


def test_partition_pptx_raises_with_neither():
    with pytest.raises(ValueError):
        partition_pptx()


class DescribePptxPartitionerShapeOrderingBehaviors:
    """Tests related to shape inclusion and ordering based on position."""

    def it_recurses_into_group_shapes(self):
        elements = cast(
            Iterator[Text],
            _PptxPartitioner(
                get_test_file_path("group-shapes-nested.pptx"),
            )._iter_presentation_elements(),
        )

        assert [e.text for e in elements] == ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]


# == DescribePptxPartitionerPageBreakBehaviors ===================================================


def test_partition_pptx_adds_page_breaks(tmp_path: pathlib.Path):
    filename = str(tmp_path / "test-page-breaks.pptx")

    presentation = pptx.Presentation()
    blank_slide_layout = presentation.slide_layouts[6]

    slide = presentation.slides.add_slide(blank_slide_layout)
    left = top = width = height = Inches(2)
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.text = "This is the first slide."

    slide = presentation.slides.add_slide(blank_slide_layout)
    left = top = width = height = Inches(2)
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.text = "This is the second slide."

    presentation.save(filename)

    elements = partition_pptx(filename=filename)

    assert elements == [
        NarrativeText(text="This is the first slide."),
        PageBreak(text=""),
        NarrativeText(text="This is the second slide."),
    ]
    for element in elements:
        assert element.metadata.filename == "test-page-breaks.pptx"


def test_partition_pptx_page_breaks_toggle_off(tmp_path: pathlib.Path):
    filename = str(tmp_path / "test-page-breaks.pptx")

    presentation = pptx.Presentation()
    blank_slide_layout = presentation.slide_layouts[6]

    slide = presentation.slides.add_slide(blank_slide_layout)
    left = top = width = height = Inches(2)
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.text = "This is the first slide."

    slide = presentation.slides.add_slide(blank_slide_layout)
    left = top = width = height = Inches(2)
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.text = "This is the second slide."

    presentation.save(filename)

    elements = partition_pptx(filename=filename, include_page_breaks=False)

    assert elements == [
        NarrativeText(text="This is the first slide."),
        NarrativeText(text="This is the second slide."),
    ]
    for element in elements:
        assert element.metadata.filename == "test-page-breaks.pptx"


def test_partition_pptx_many_pages():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point-many-pages.pptx")
    elements = partition_pptx(filename=filename)

    # The page_number of PageBreak is None
    assert set(filter(None, (elt.metadata.page_number for elt in elements))) == {1, 2}
    for element in elements:
        assert element.metadata.filename == "fake-power-point-many-pages.pptx"


# == DescribePptxPartitionerMiscellaneousBehaviors ===============================================


def test_partition_pptx_orders_elements(tmp_path: pathlib.Path):
    filename = str(tmp_path / "test-ordering.pptx")
    presentation = pptx.Presentation()
    blank_slide_layout = presentation.slide_layouts[6]
    slide = presentation.slides.add_slide(blank_slide_layout)

    left = top = width = height = Inches(2)
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.text = "This is lower and should come second"

    left = top = width = height = Inches(1)
    left = top = Inches(-10)
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.text = "This is off the page and shouldn't appear"

    left = top = width = height = Inches(2)
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.text = ""

    left = top = width = height = Inches(1)
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.text = "This is higher and should come first"

    top = width = height = Inches(1)
    left = Inches(0.5)
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.text = "-------------TOP-------------"

    presentation.save(filename)

    elements = partition_pptx(filename=filename)
    assert elements == [
        Text("-------------TOP-------------"),
        NarrativeText("This is higher and should come first"),
        NarrativeText("This is lower and should come second"),
    ]
    for element in elements:
        assert element.metadata.filename == "test-ordering.pptx"


EXPECTED_HTML_TABLE = """<table>
<thead>
<tr><th>Column 1  </th><th>Column 2  </th><th>Column 3  </th></tr>
</thead>
<tbody>
<tr><td>Red       </td><td>Green     </td><td>Blue      </td></tr>
<tr><td>Purple    </td><td>Orange    </td><td>Yellow    </td></tr>
<tr><td>Tangerine </td><td>Pink      </td><td>Aqua      </td></tr>
</tbody>
</table>"""


def test_partition_pptx_grabs_tables():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point-table.pptx")
    elements = cast(Sequence[Text], partition_pptx(filename=filename))

    assert elements[1].text.startswith("Column 1")
    assert elements[1].text.strip().endswith("Aqua")
    assert elements[1].metadata.text_as_html == EXPECTED_HTML_TABLE
    assert elements[1].metadata.filename == "fake-power-point-table.pptx"


@pytest.mark.parametrize(
    "infer_table_structure",
    [
        True,
        False,
    ],
)
def test_partition_pptx_infer_table_structure(infer_table_structure):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point-table.pptx")
    elements = cast(
        Sequence[Text],
        partition_pptx(filename=filename, infer_table_structure=infer_table_structure),
    )
    table_element_has_text_as_html_field = (
        hasattr(elements[1].metadata, "text_as_html")
        and elements[1].metadata.text_as_html is not None
    )
    assert table_element_has_text_as_html_field == infer_table_structure


def test_partition_pptx_malformed():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point-malformed.pptx")
    elements = cast(Sequence[Text], partition_pptx(filename=filename))

    assert elements[0].text == "Problem Date Placeholder"
    assert elements[1].text == "Test Slide"
    for element in elements:
        assert element.metadata.filename == "fake-power-point-malformed.pptx"


# == DescribePptxPartitionerMetadataBehaviors ====================================================


def test_partition_pptx_from_filename_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    elements = partition_pptx(filename=filename, include_metadata=False)
    assert elements == EXPECTED_PPTX_OUTPUT


def test_partition_pptx_from_file_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    with open(filename, "rb") as f:
        elements = partition_pptx(file=f, include_metadata=False)
    assert elements == EXPECTED_PPTX_OUTPUT


def test_partition_pptx_metadata_date(mocker: MockFixture):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point-malformed.pptx")
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pptx.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_pptx(
        filename=filename,
    )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_pptx_with_custom_metadata_date(mocker: MockFixture):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point-malformed.pptx")
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pptx.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_pptx(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_pptx_from_file_metadata_date(mocker: MockFixture):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point-malformed.pptx")
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pptx.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_pptx(
            file=f,
        )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_pptx_from_file_with_custom_metadata_date(mocker: MockFixture):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point-malformed.pptx")
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pptx.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_pptx(file=f, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_pptx_element_metadata_has_languages():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    elements = partition_pptx(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_pptx_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.pptx"
    elements = partition_pptx(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    # languages other than English and Spanish are detected by this partitioner,
    # so this test is slightly different from the other partition tests
    langs = {element.metadata.languages[0] for element in elements if element.metadata.languages}
    assert "eng" in langs
    assert "spa" in langs


def test_partition_pptx_raises_TypeError_for_invalid_languages():
    with pytest.raises(TypeError):
        filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
        partition_pptx(filename=filename, languages="eng")  # type: ignore


# == DescribePptxPartitionerDownstreamBehaviors ==================================================


def test_partition_pptx_with_json():
    elements = partition_pptx(example_doc_path("fake-power-point.pptx"))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_by_title_on_partition_pptx():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "science-exploration-1p.pptx")
    elements = partition_pptx(filename=filename)
    chunk_elements = partition_pptx(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_pptx_title_shape_detection(tmp_path: pathlib.Path):
    """This tests if the title attribute of a shape is correctly categorized as a title"""
    filename = str(tmp_path / "test-title-shape.pptx")

    # create a fake PowerPoint presentation with a slide containing a title shape
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_shape = slide.shapes.title
    title_shape.text = (
        "This is a title, it's a bit long so we can make sure it's not narrative text"
    )
    title_shape.text_frame.add_paragraph().text = "this is a subtitle"

    prs.save(filename)

    # partition the PowerPoint presentation and get the first element
    elements = partition_pptx(filename)
    title = elements[0]
    subtitle = elements[1]

    # assert that the first line is a title and has the correct text and depth
    assert isinstance(title, Title)
    assert (
        title.text == "This is a title, it's a bit long so we can make sure it's not narrative text"
    )
    assert title.metadata.category_depth == 0

    # assert that the first line is the subtitle and has the correct text and depth
    assert isinstance(subtitle, Title)
    assert subtitle.text == "this is a subtitle"
    assert subtitle.metadata.category_depth == 1


def test_partition_pptx_level_detection(tmp_path: pathlib.Path):
    """This tests if the level attribute of a paragraph is correctly set as the category depth"""
    filename = str(tmp_path / "test-category-depth.pptx")

    prs = pptx.Presentation()
    blank_slide_layout = prs.slide_layouts[1]

    slide = prs.slides.add_slide(blank_slide_layout)
    shapes = slide.shapes
    title_shape = shapes.title
    body_shape = shapes.placeholders[1]
    title_shape.text = (
        "This is a title, it's a bit long so we can make sure it's not narrative text"
    )

    tf = body_shape.text_frame
    tf.text = "this is the root level bullet"

    p = tf.add_paragraph()
    p.text = "this is the level 1 bullet"
    p.level = 1

    p = tf.add_paragraph()
    p.text = "this is the level 2 bullet"
    p.level = 2

    prs.slides[0].shapes

    prs.save(filename)

    # partition the PowerPoint presentation and get the first element
    elements = partition_pptx(filename)

    # NOTE(newelh) - python_pptx does not create full bullet xml, so unstructured will
    #                not detect the paragraphs as bullets. This is fine for now, as
    #                the level attribute is still set correctly, and what we're testing here
    test_cases = [
        (0, Title, "This is a title, it's a bit long so we can make sure it's not narrative text"),
        (0, NarrativeText, "this is the root level bullet"),
        (1, NarrativeText, "this is the level 1 bullet"),
        (2, NarrativeText, "this is the level 2 bullet"),
    ]

    for element, test_case in zip(elements, test_cases):
        assert element.text == test_case[2], f"expected {test_case[2]}, got {element.text}"
        assert isinstance(
            element,
            test_case[1],
        ), f"expected {test_case[1]}, got {element.category} for {element.text}"
        assert (
            element.metadata.category_depth == test_case[0]
        ), f"expected {test_case[0]}, got {element.metadata.category_depth} for {element.text}"


def test_partition_pptx_hierarchy_sample_document():
    """This tests if the hierarchy of the sample document is correctly detected"""
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "sample-presentation.pptx")
    elements = partition_pptx(filename=filename)

    test_cases = [
        # (expected category depth, parent id, child id)
        (0, None, "8e924068ead7acb8b7217a9edbea21d4"),
        (1, "8e924068ead7acb8b7217a9edbea21d4", "32dc828e353aa33bbdf112787389d5dd"),
        (None, None, "e3b0c44298fc1c149afbf4c8996fb924"),
        (0, None, "4485990848f79de686029af6e720eed0"),
        (0, "4485990848f79de686029af6e720eed0", "b4e4ef35880d1f7e82272f7ae8194baa"),
        (0, "4485990848f79de686029af6e720eed0", "44a398d215d79c2128055d2acfe8ab69"),
        (1, "44a398d215d79c2128055d2acfe8ab69", "dbbf18a38f846b5790c75ba8ad649704"),
        (1, "44a398d215d79c2128055d2acfe8ab69", "d75cf41cbf1c4421328729de8e467b02"),
        (2, "d75cf41cbf1c4421328729de8e467b02", "27597b7305a7b8e066a6378413566d2e"),
        (0, "4485990848f79de686029af6e720eed0", "1761b6f5d23781670b3c9b870804069f"),
        (None, None, "e3b0c44298fc1c149afbf4c8996fb924"),
        (0, None, "4a6dc2d15e7a98e9871a1eb60496059e"),
        (0, "4a6dc2d15e7a98e9871a1eb60496059e", "c4bac691bfd883bff86dce2d7a6b9943"),
        (0, "4a6dc2d15e7a98e9871a1eb60496059e", "61eda8e6c9b22845a1aa3d329cce15ef"),
        (1, "61eda8e6c9b22845a1aa3d329cce15ef", "ad54bee56405cf3878f91f5c97a2395b"),
        (1, "61eda8e6c9b22845a1aa3d329cce15ef", "4d85745729954cd77e0f49ceced49f32"),
        (2, "4d85745729954cd77e0f49ceced49f32", "5cea03d706c6246b120034246b893101"),
        (0, "4a6dc2d15e7a98e9871a1eb60496059e", "cdf71e4210241bd78b1032e2f44d104f"),
        (0, "4a6dc2d15e7a98e9871a1eb60496059e", "ecb3d1d718b7fd75701a33e56fc131dd"),
        (0, "4a6dc2d15e7a98e9871a1eb60496059e", "cc598a5e8c911a7c5cecedf4959652aa"),
        (1, "cc598a5e8c911a7c5cecedf4959652aa", "305ae9618b7f8ba84925c9e7e49034c2"),
        (1, "cc598a5e8c911a7c5cecedf4959652aa", "cce1c1d6646a92ffdc883c573c765da9"),
        (2, "cce1c1d6646a92ffdc883c573c765da9", "af8beec1131e6df4758e081e878bf775"),
        (0, "4a6dc2d15e7a98e9871a1eb60496059e", "ddf389d07353b7a3e03aa138f42dfd89"),
        (None, None, "e3b0c44298fc1c149afbf4c8996fb924"),
        (None, None, "2332cdaa45717e70444e2de313605e22"),
        (0, None, "7ba0daa8739310f1b39736b3ffe3dea2"),
    ]

    # Zip the test cases with the elements
    for element, test_case in zip(elements, test_cases):
        assert element.metadata.category_depth == test_case[0]
        assert element.metadata.parent_id == test_case[1]
        assert element.id == test_case[2]
