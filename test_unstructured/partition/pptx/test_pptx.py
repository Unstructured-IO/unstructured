# pyright: reportPrivateUsage=false

"""Test suite for `unstructured.partition.pptx` module."""

import os
import pathlib
from typing import Iterator, Sequence, cast

import pptx
import pytest
from pptx.util import Inches
from pytest_mock import MockFixture

from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    ListItem,
    NarrativeText,
    PageBreak,
    Text,
    Title,
)
from unstructured.partition.json import partition_json
from unstructured.partition.pptx import _PptxPartitioner, partition_pptx
from unstructured.staging.base import elements_to_json

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


# == DescribePptxPartitionerDownstreamBehaviors ==================================================


def test_partition_pptx_with_json():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    elements = partition_pptx(filename=filename)
    test_elements = partition_json(text=elements_to_json(elements))

    assert len(elements) == len(test_elements)
    assert elements[0].metadata.filename == test_elements[0].metadata.filename

    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


def test_add_chunking_strategy_on_partition_pptx():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    elements = partition_pptx(filename=filename)
    chunk_elements = partition_pptx(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks
