import numpy as np
import pytest
from PIL import Image

from unstructured_inference.inference.elements import (
    EmbeddedTextRegion,
    Rectangle,
    TextRegion,
)
from unstructured_inference.inference.layoutelement import LayoutElement


@pytest.fixture
def mock_pil_image():
    return Image.new("RGB", (50, 50))


@pytest.fixture
def mock_numpy_image():
    return np.zeros((50, 50, 3), np.uint8)


@pytest.fixture
def mock_rectangle():
    return Rectangle(100, 100, 300, 300)


@pytest.fixture
def mock_text_region():
    return TextRegion.from_coords(100, 100, 300, 300, text="Sample text")


@pytest.fixture
def mock_layout_element():
    return LayoutElement.from_coords(
        100,
        100,
        300,
        300,
        text="Sample text",
        source=None,
        type="Text",
    )


@pytest.fixture
def mock_embedded_text_regions():
    return [
        EmbeddedTextRegion.from_coords(
            x1=453.00277777777774,
            y1=317.319341111111,
            x2=711.5338541666665,
            y2=358.28571222222206,
            text="LayoutParser:",
        ),
        EmbeddedTextRegion.from_coords(
            x1=726.4778125,
            y1=317.319341111111,
            x2=760.3308594444444,
            y2=357.1698966666667,
            text="A",
        ),
        EmbeddedTextRegion.from_coords(
            x1=775.2748177777777,
            y1=317.319341111111,
            x2=917.3579885555555,
            y2=357.1698966666667,
            text="Unified",
        ),
        EmbeddedTextRegion.from_coords(
            x1=932.3019468888888,
            y1=317.319341111111,
            x2=1071.8426522222221,
            y2=357.1698966666667,
            text="Toolkit",
        ),
        EmbeddedTextRegion.from_coords(
            x1=1086.7866105555556,
            y1=317.319341111111,
            x2=1141.2105142777777,
            y2=357.1698966666667,
            text="for",
        ),
        EmbeddedTextRegion.from_coords(
            x1=1156.154472611111,
            y1=317.319341111111,
            x2=1256.334784222222,
            y2=357.1698966666667,
            text="Deep",
        ),
        EmbeddedTextRegion.from_coords(
            x1=437.83888888888885,
            y1=367.13322999999986,
            x2=610.0171992222222,
            y2=406.9837855555556,
            text="Learning",
        ),
        EmbeddedTextRegion.from_coords(
            x1=624.9611575555555,
            y1=367.13322999999986,
            x2=741.6754646666665,
            y2=406.9837855555556,
            text="Based",
        ),
        EmbeddedTextRegion.from_coords(
            x1=756.619423,
            y1=367.13322999999986,
            x2=958.3867708333332,
            y2=406.9837855555556,
            text="Document",
        ),
        EmbeddedTextRegion.from_coords(
            x1=973.3307291666665,
            y1=367.13322999999986,
            x2=1092.0535042777776,
            y2=406.9837855555556,
            text="Image",
        ),
    ]


# TODO(alan): Make a better test layout
@pytest.fixture
def mock_layout(mock_embedded_text_regions):
    return [
        LayoutElement(text=r.text, type="UncategorizedText", bbox=r.bbox)
        for r in mock_embedded_text_regions
    ]


@pytest.fixture
def example_table_cells():
    cells = [
        {"cell text": "Disability Category", "row_nums": [0, 1], "column_nums": [0]},
        {"cell text": "Participants", "row_nums": [0, 1], "column_nums": [1]},
        {"cell text": "Ballots Completed", "row_nums": [0, 1], "column_nums": [2]},
        {"cell text": "Ballots Incomplete/Terminated", "row_nums": [0, 1], "column_nums": [3]},
        {"cell text": "Results", "row_nums": [0], "column_nums": [4, 5]},
        {"cell text": "Accuracy", "row_nums": [1], "column_nums": [4]},
        {"cell text": "Time to complete", "row_nums": [1], "column_nums": [5]},
        {"cell text": "Blind", "row_nums": [2], "column_nums": [0]},
        {"cell text": "Low Vision", "row_nums": [3], "column_nums": [0]},
        {"cell text": "Dexterity", "row_nums": [4], "column_nums": [0]},
        {"cell text": "Mobility", "row_nums": [5], "column_nums": [0]},
        {"cell text": "5", "row_nums": [2], "column_nums": [1]},
        {"cell text": "5", "row_nums": [3], "column_nums": [1]},
        {"cell text": "5", "row_nums": [4], "column_nums": [1]},
        {"cell text": "3", "row_nums": [5], "column_nums": [1]},
        {"cell text": "1", "row_nums": [2], "column_nums": [2]},
        {"cell text": "2", "row_nums": [3], "column_nums": [2]},
        {"cell text": "4", "row_nums": [4], "column_nums": [2]},
        {"cell text": "3", "row_nums": [5], "column_nums": [2]},
        {"cell text": "4", "row_nums": [2], "column_nums": [3]},
        {"cell text": "3", "row_nums": [3], "column_nums": [3]},
        {"cell text": "1", "row_nums": [4], "column_nums": [3]},
        {"cell text": "0", "row_nums": [5], "column_nums": [3]},
        {"cell text": "34.5%, n=1", "row_nums": [2], "column_nums": [4]},
        {"cell text": "98.3% n=2 (97.7%, n=3)", "row_nums": [3], "column_nums": [4]},
        {"cell text": "98.3%, n=4", "row_nums": [4], "column_nums": [4]},
        {"cell text": "95.4%, n=3", "row_nums": [5], "column_nums": [4]},
        {"cell text": "1199 sec, n=1", "row_nums": [2], "column_nums": [5]},
        {"cell text": "1716 sec, n=3 (1934 sec, n=2)", "row_nums": [3], "column_nums": [5]},
        {"cell text": "1672.1 sec, n=4", "row_nums": [4], "column_nums": [5]},
        {"cell text": "1416 sec, n=3", "row_nums": [5], "column_nums": [5]},
    ]
    for i in range(len(cells)):
        cells[i]["column header"] = False
    return [cells]
