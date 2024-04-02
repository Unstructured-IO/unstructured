# pyright: reportPrivateUsage=false

"""Test suite for `unstructured.partition.pptx` module."""

import os
import pathlib
from tempfile import SpooledTemporaryFile

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
        elements = _PptxPartitioner(
            get_test_file_path("group-shapes-nested.pptx")
        )._iter_presentation_elements()

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
    elements = partition_pptx(filename=filename)

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
    elements = partition_pptx(filename=filename, infer_table_structure=infer_table_structure)
    table_element_has_text_as_html_field = (
        hasattr(elements[1].metadata, "text_as_html")
        and elements[1].metadata.text_as_html is not None
    )
    assert table_element_has_text_as_html_field == infer_table_structure


def test_partition_pptx_malformed():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point-malformed.pptx")
    elements = partition_pptx(filename=filename)

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

    assert elements[0].metadata.last_modified is None


def test_partition_pptx_from_file_explicit_get_metadata_date(mocker: MockFixture):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point-malformed.pptx")
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pptx.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_pptx(file=f, date_from_file_object=True)

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


def test_partition_pptx_from_file_without_metadata_date():
    """Test partition_pptx() with file that are not possible to get last modified date"""
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point-malformed.pptx")
    with open(filename, "rb") as f:
        sf = SpooledTemporaryFile()
        sf.write(f.read())
        sf.seek(0)
        elements = partition_pptx(file=sf, date_from_file_object=True)

    assert elements[0].metadata.last_modified is None


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
        (0, None, "e5402c930a0b94d32fe23c852c9d77be"),
        (1, "e5402c930a0b94d32fe23c852c9d77be", "3dd909002d2bb57248e6f28ada709301"),
        (None, None, "a783370f88d8c54b5f5e6641af69d86d"),
        (0, None, "0182719c4aaa433f96cb01a96687c0e7"),
        (0, "0182719c4aaa433f96cb01a96687c0e7", "d7384a252a01ac5db8da97bf415b5c36"),
        (0, "0182719c4aaa433f96cb01a96687c0e7", "f817ddfffec1f93eccb19c0eb7565e35"),
        (1, "f817ddfffec1f93eccb19c0eb7565e35", "8abeb3b69713d24fa8c322f6e69adf83"),
        (1, "f817ddfffec1f93eccb19c0eb7565e35", "12dbca0eb94499d9219c92f1c65f4e46"),
        (2, "12dbca0eb94499d9219c92f1c65f4e46", "805a519158270e2cbc17bb5adc4f2b8b"),
        (0, "0182719c4aaa433f96cb01a96687c0e7", "ce6a17388673af01739d066d9a174737"),
        (None, None, "6b37173e9c5180e77bfe620773f2ef81"),
        (0, None, "315541a99d79e0b050fe99e6ea646bf6"),
        (0, "315541a99d79e0b050fe99e6ea646bf6", "278469a2b1e5d76e6b9735ede8091f2f"),
        (0, "315541a99d79e0b050fe99e6ea646bf6", "c7e20e9f9f8deb5b0642daa42fc78fd4"),
        (1, "c7e20e9f9f8deb5b0642daa42fc78fd4", "5077cc8719c4f5b8252d0085cc42224a"),
        (1, "c7e20e9f9f8deb5b0642daa42fc78fd4", "4d164a2b44a63f2f0f92e4eec4380af7"),
        (2, "4d164a2b44a63f2f0f92e4eec4380af7", "d20c486956fd3397ddbb053be1baa954"),
        (0, "315541a99d79e0b050fe99e6ea646bf6", "7011d45f68e7c9e769fee435fe03a803"),
        (0, "315541a99d79e0b050fe99e6ea646bf6", "cfe3f81ebadf83b67cfb91f51d9f6e56"),
        (0, "315541a99d79e0b050fe99e6ea646bf6", "78d717b1928087bff2caff0ea963e3ec"),
        (1, "78d717b1928087bff2caff0ea963e3ec", "0a350d3e3f376e925dfccde745337260"),
        (1, "78d717b1928087bff2caff0ea963e3ec", "54f147e060346d1c3834f067a5bd6048"),
        (2, "54f147e060346d1c3834f067a5bd6048", "d0672747b172d2eca5e85daecd6f67d3"),
        (0, "315541a99d79e0b050fe99e6ea646bf6", "670b2beffbb7001b720ba3d0eab64d5d"),
        (None, None, "5de06d929dcbbc49c0948cde7d6d9478"),
        (None, None, "9489177bc5f638497d3d6926bb2a5201"),
        (0, None, "d16c20dabfef7e1cd2974c4ee4f311de"),
    ]

    # Zip the test cases with the elements
    for element, test_case in zip(elements, test_cases):
        expected_depth, expected_parent_id, expected_id = test_case
        assert element.metadata.category_depth == expected_depth
        assert element.metadata.parent_id == expected_parent_id
        assert element.id == expected_id
