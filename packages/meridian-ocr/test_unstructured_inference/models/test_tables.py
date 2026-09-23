import os
import threading
from copy import deepcopy

import numpy as np
import pytest
import torch
from PIL import Image
from transformers.models.table_transformer.modeling_table_transformer import (
    TableTransformerDecoder,
)

import unstructured_inference.models.table_postprocess as postprocess
from unstructured_inference.models import tables
from unstructured_inference.models.tables import (
    apply_thresholds_on_objects,
    structure_to_cells,
)

skip_outside_ci = os.getenv("CI", "").lower() in {"", "false", "f", "0"}


@pytest.fixture
def table_transformer():
    tables.load_agent()
    return tables.tables_agent


def test_load_agent(table_transformer):
    assert hasattr(table_transformer, "model")


@pytest.fixture
def example_image():
    return Image.open("./sample-docs/table-multi-row-column-cells.png").convert("RGB")


@pytest.fixture
def mocked_ocr_tokens():
    return [
        {
            "bbox": [51.0, 37.0, 1333.0, 38.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 0,
            "text": " ",
        },
        {
            "bbox": [1064.0, 47.0, 1161.0, 71.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 1,
            "text": "Results",
        },
        {
            "bbox": [891.0, 113.0, 1333.0, 114.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 2,
            "text": " ",
        },
        {
            "bbox": [51.0, 236.0, 1333.0, 237.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 3,
            "text": " ",
        },
        {
            "bbox": [51.0, 308.0, 1333.0, 309.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 4,
            "text": " ",
        },
        {
            "bbox": [51.0, 450.0, 1333.0, 452.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 5,
            "text": " ",
        },
        {
            "bbox": [51.0, 522.0, 1333.0, 524.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 6,
            "text": " ",
        },
        {
            "bbox": [51.0, 37.0, 53.0, 596.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 7,
            "text": " ",
        },
        {
            "bbox": [90.0, 89.0, 167.0, 93.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 8,
            "text": "soa",
        },
        {
            "bbox": [684.0, 68.0, 762.0, 91.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 9,
            "text": "Ballot:",
        },
        {
            "bbox": [69.0, 84.0, 196.0, 140.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 10,
            "text": "etealeiliay",
        },
        {
            "bbox": [283.0, 109.0, 446.0, 132.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 11,
            "text": "Participants",
        },
        {
            "bbox": [484.0, 84.0, 576.0, 140.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 12,
            "text": "pallets",
        },
        {
            "bbox": [684.0, 75.0, 776.0, 132.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 13,
            "text": "incom",
        },
        {
            "bbox": [788.0, 107.0, 853.0, 136.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 14,
            "text": "lete/",
        },
        {
            "bbox": [68.0, 121.0, 191.0, 162.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 15,
            "text": "Category",
        },
        {
            "bbox": [371.0, 115.0, 386.0, 137.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 16,
            "text": "P",
        },
        {
            "bbox": [483.0, 121.0, 632.0, 162.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 17,
            "text": "Completed",
        },
        {
            "bbox": [756.0, 115.0, 785.0, 154.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 18,
            "text": "Ne",
        },
        {
            "bbox": [930.0, 125.0, 1054.0, 152.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 19,
            "text": "Accuracy",
        },
        {
            "bbox": [1159.0, 124.0, 1227.0, 147.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 20,
            "text": "Time",
        },
        {
            "bbox": [1235.0, 126.0, 1264.0, 147.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 21,
            "text": "to",
        },
        {
            "bbox": [682.0, 149.0, 841.0, 173.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 22,
            "text": "Terminated",
        },
        {
            "bbox": [1147.0, 169.0, 1276.0, 198.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 23,
            "text": "complete",
        },
        {
            "bbox": [70.0, 245.0, 127.0, 266.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 24,
            "text": "Blind",
        },
        {
            "bbox": [361.0, 247.0, 373.0, 266.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 25,
            "text": "5",
        },
        {
            "bbox": [562.0, 247.0, 573.0, 266.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 26,
            "text": "1",
        },
        {
            "bbox": [772.0, 247.0, 786.0, 266.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 27,
            "text": "4",
        },
        {
            "bbox": [925.0, 246.0, 1005.0, 270.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 28,
            "text": "34.5%,",
        },
        {
            "bbox": [1017.0, 247.0, 1059.0, 266.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 29,
            "text": "n=1",
        },
        {
            "bbox": [1129.0, 246.0, 1187.0, 266.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 30,
            "text": "1199",
        },
        {
            "bbox": [1197.0, 251.0, 1241.0, 270.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 31,
            "text": "sec,",
        },
        {
            "bbox": [1253.0, 247.0, 1295.0, 266.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 32,
            "text": "n=1",
        },
        {
            "bbox": [70.0, 319.0, 117.0, 338.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 33,
            "text": "Low",
        },
        {
            "bbox": [125.0, 318.0, 198.0, 338.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 34,
            "text": "Vision",
        },
        {
            "bbox": [361.0, 319.0, 373.0, 338.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 35,
            "text": "5",
        },
        {
            "bbox": [561.0, 318.0, 573.0, 338.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 36,
            "text": "2",
        },
        {
            "bbox": [773.0, 318.0, 785.0, 338.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 37,
            "text": "3",
        },
        {
            "bbox": [928.0, 318.0, 1002.0, 339.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 38,
            "text": "98.3%",
        },
        {
            "bbox": [1013.0, 318.0, 1055.0, 338.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 39,
            "text": "n=2",
        },
        {
            "bbox": [1129.0, 318.0, 1188.0, 338.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 40,
            "text": "1716",
        },
        {
            "bbox": [1197.0, 323.0, 1242.0, 342.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 41,
            "text": "sec,",
        },
        {
            "bbox": [1253.0, 318.0, 1295.0, 338.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 42,
            "text": "n=3",
        },
        {
            "bbox": [916.0, 387.0, 1005.0, 413.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 43,
            "text": "(97.7%,",
        },
        {
            "bbox": [1016.0, 387.0, 1068.0, 413.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 44,
            "text": "n=3)",
        },
        {
            "bbox": [1086.0, 383.0, 1099.0, 418.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 45,
            "text": "|",
        },
        {
            "bbox": [1120.0, 387.0, 1188.0, 413.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 46,
            "text": "(1934",
        },
        {
            "bbox": [1197.0, 393.0, 1241.0, 412.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 47,
            "text": "sec,",
        },
        {
            "bbox": [1253.0, 387.0, 1305.0, 413.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 48,
            "text": "n=2)",
        },
        {
            "bbox": [70.0, 456.0, 181.0, 489.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 49,
            "text": "Dexterity",
        },
        {
            "bbox": [360.0, 461.0, 372.0, 480.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 50,
            "text": "5",
        },
        {
            "bbox": [560.0, 461.0, 574.0, 480.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 51,
            "text": "4",
        },
        {
            "bbox": [774.0, 461.0, 785.0, 480.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 52,
            "text": "1",
        },
        {
            "bbox": [924.0, 460.0, 1005.0, 484.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 53,
            "text": "98.3%,",
        },
        {
            "bbox": [1017.0, 461.0, 1060.0, 480.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 54,
            "text": "n=4",
        },
        {
            "bbox": [1118.0, 460.0, 1199.0, 480.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 55,
            "text": "1672.1",
        },
        {
            "bbox": [1209.0, 465.0, 1253.0, 484.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 56,
            "text": "sec,",
        },
        {
            "bbox": [1265.0, 461.0, 1308.0, 480.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 57,
            "text": "n=4",
        },
        {
            "bbox": [70.0, 527.0, 170.0, 561.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 58,
            "text": "Mobility",
        },
        {
            "bbox": [361.0, 532.0, 373.0, 552.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 59,
            "text": "3",
        },
        {
            "bbox": [561.0, 532.0, 573.0, 552.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 60,
            "text": "3",
        },
        {
            "bbox": [773.0, 532.0, 786.0, 552.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 61,
            "text": "0",
        },
        {
            "bbox": [924.0, 532.0, 1005.0, 556.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 62,
            "text": "95.4%,",
        },
        {
            "bbox": [1017.0, 532.0, 1059.0, 552.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 63,
            "text": "n=3",
        },
        {
            "bbox": [1129.0, 532.0, 1188.0, 552.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 64,
            "text": "1416",
        },
        {
            "bbox": [1197.0, 537.0, 1242.0, 556.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 65,
            "text": "sec,",
        },
        {
            "bbox": [1253.0, 532.0, 1295.0, 552.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 66,
            "text": "n=3",
        },
        {
            "bbox": [266.0, 37.0, 267.0, 596.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 67,
            "text": " ",
        },
        {
            "bbox": [466.0, 37.0, 468.0, 596.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 68,
            "text": " ",
        },
        {
            "bbox": [666.0, 37.0, 668.0, 596.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 69,
            "text": " ",
        },
        {
            "bbox": [891.0, 37.0, 893.0, 596.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 70,
            "text": " ",
        },
        {
            "bbox": [1091.0, 113.0, 1093.0, 596.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 71,
            "text": " ",
        },
        {
            "bbox": [51.0, 595.0, 1333.0, 596.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 72,
            "text": " ",
        },
        {
            "bbox": [1331.0, 37.0, 1333.0, 596.0],
            "block_num": 0,
            "line_num": 0,
            "span_num": 73,
            "text": " ",
        },
    ]


@pytest.mark.parametrize(
    "model_path",
    [
        ("invalid_table_path"),
        ("incorrect_table_path"),
    ],
)
def test_load_table_model_raises_when_not_available(model_path):
    with pytest.raises(OSError):
        table_model = tables.UnstructuredTableTransformerModel()
        table_model.initialize(model=model_path)


@pytest.mark.parametrize(
    ("bbox1", "bbox2", "expected_result"),
    [
        ((0, 0, 5, 5), (2, 2, 7, 7), 0.36),
        ((0, 0, 0, 0), (6, 6, 10, 10), 0),
    ],
)
def test_iob(bbox1, bbox2, expected_result):
    result = tables.iob(bbox1, bbox2)
    assert result == expected_result


@pytest.mark.parametrize(
    "model_path",
    [
        "microsoft/table-transformer-structure-recognition",
    ],
)
def test_load_donut_model(model_path):
    table_model = tables.UnstructuredTableTransformerModel()
    table_model.initialize(model=model_path)
    assert type(table_model.model.model.decoder) is TableTransformerDecoder


@pytest.mark.parametrize(
    ("input_test", "output_test"),
    [
        (
            [
                {
                    "label": "table column header",
                    "score": 0.9349299073219299,
                    "bbox": [
                        47.83147430419922,
                        116.8877944946289,
                        2557.79296875,
                        216.98883056640625,
                    ],
                },
                {
                    "label": "table column header",
                    "score": 0.934,
                    "bbox": [
                        47.83147430419922,
                        116.8877944946289,
                        2557.79296875,
                        216.98883056640625,
                    ],
                },
            ],
            [
                {
                    "label": "table column header",
                    "score": 0.9349299073219299,
                    "bbox": [
                        47.83147430419922,
                        116.8877944946289,
                        2557.79296875,
                        216.98883056640625,
                    ],
                },
            ],
        ),
        ([], []),
    ],
)
def test_nms(input_test, output_test):
    output = postprocess.nms(input_test)

    assert output == output_test


@pytest.mark.parametrize(
    ("supercell1", "supercell2"),
    [
        (
            {
                "label": "table spanning cell",
                "score": 0.526617169380188,
                "bbox": [
                    1446.2801513671875,
                    1023.817138671875,
                    2114.3525390625,
                    1099.20166015625,
                ],
                "projected row header": False,
                "header": False,
                "row_numbers": [3, 4],
                "column_numbers": [0, 4],
            },
            {
                "label": "table spanning cell",
                "score": 0.5199193954467773,
                "bbox": [
                    98.92312622070312,
                    676.1566772460938,
                    751.0982666015625,
                    938.5986938476562,
                ],
                "projected row header": False,
                "header": False,
                "row_numbers": [3, 4, 6],
                "column_numbers": [0, 4],
            },
        ),
        (
            {
                "label": "table spanning cell",
                "score": 0.526617169380188,
                "bbox": [
                    1446.2801513671875,
                    1023.817138671875,
                    2114.3525390625,
                    1099.20166015625,
                ],
                "projected row header": False,
                "header": False,
                "row_numbers": [3, 4],
                "column_numbers": [0, 4],
            },
            {
                "label": "table spanning cell",
                "score": 0.5199193954467773,
                "bbox": [
                    98.92312622070312,
                    676.1566772460938,
                    751.0982666015625,
                    938.5986938476562,
                ],
                "projected row header": False,
                "header": False,
                "row_numbers": [4],
                "column_numbers": [0, 4, 6],
            },
        ),
        (
            {
                "label": "table spanning cell",
                "score": 0.526617169380188,
                "bbox": [
                    1446.2801513671875,
                    1023.817138671875,
                    2114.3525390625,
                    1099.20166015625,
                ],
                "projected row header": False,
                "header": False,
                "row_numbers": [3, 4],
                "column_numbers": [1, 4],
            },
            {
                "label": "table spanning cell",
                "score": 0.5199193954467773,
                "bbox": [
                    98.92312622070312,
                    676.1566772460938,
                    751.0982666015625,
                    938.5986938476562,
                ],
                "projected row header": False,
                "header": False,
                "row_numbers": [4],
                "column_numbers": [0, 4, 6],
            },
        ),
        (
            {
                "label": "table spanning cell",
                "score": 0.526617169380188,
                "bbox": [
                    1446.2801513671875,
                    1023.817138671875,
                    2114.3525390625,
                    1099.20166015625,
                ],
                "projected row header": False,
                "header": False,
                "row_numbers": [3, 4],
                "column_numbers": [1, 4],
            },
            {
                "label": "table spanning cell",
                "score": 0.5199193954467773,
                "bbox": [
                    98.92312622070312,
                    676.1566772460938,
                    751.0982666015625,
                    938.5986938476562,
                ],
                "projected row header": False,
                "header": False,
                "row_numbers": [2, 4, 5, 6, 7, 8],
                "column_numbers": [0, 4, 6],
            },
        ),
    ],
)
def test_remove_supercell_overlap(supercell1, supercell2):
    assert postprocess.remove_supercell_overlap(supercell1, supercell2) is None


@pytest.mark.parametrize(
    ("supercells", "rows", "columns", "output_test"),
    [
        (
            [
                {
                    "label": "table spanning cell",
                    "score": 0.9,
                    "bbox": [
                        98.92312622070312,
                        143.11549377441406,
                        2115.197265625,
                        1238.27587890625,
                    ],
                    "projected row header": True,
                    "header": True,
                    "span": True,
                },
            ],
            [
                {
                    "label": "table row",
                    "score": 0.9299452900886536,
                    "bbox": [0, 0, 10, 10],
                    "column header": True,
                    "header": True,
                },
                {
                    "label": "table row",
                    "score": 0.9299452900886536,
                    "bbox": [
                        98.92312622070312,
                        143.11549377441406,
                        2114.3525390625,
                        193.67681884765625,
                    ],
                    "column header": True,
                    "header": True,
                },
                {
                    "label": "table row",
                    "score": 0.9299452900886536,
                    "bbox": [
                        98.92312622070312,
                        143.11549377441406,
                        2114.3525390625,
                        193.67681884765625,
                    ],
                    "column header": True,
                    "header": True,
                },
            ],
            [
                {
                    "label": "table column",
                    "score": 0.9996132254600525,
                    "bbox": [
                        98.92312622070312,
                        143.11549377441406,
                        517.6508178710938,
                        1616.48779296875,
                    ],
                },
                {
                    "label": "table column",
                    "score": 0.9935646653175354,
                    "bbox": [
                        520.0474853515625,
                        143.11549377441406,
                        751.0982666015625,
                        1616.48779296875,
                    ],
                },
            ],
            [
                {
                    "label": "table spanning cell",
                    "score": 0.9,
                    "bbox": [
                        98.92312622070312,
                        143.11549377441406,
                        751.0982666015625,
                        193.67681884765625,
                    ],
                    "projected row header": True,
                    "header": True,
                    "span": True,
                    "row_numbers": [1, 2],
                    "column_numbers": [0, 1],
                },
                {
                    "row_numbers": [0],
                    "column_numbers": [0, 1],
                    "score": 0.9,
                    "propagated": True,
                    "bbox": [
                        98.92312622070312,
                        143.11549377441406,
                        751.0982666015625,
                        193.67681884765625,
                    ],
                },
            ],
        ),
    ],
)
def test_align_supercells(supercells, rows, columns, output_test):
    assert postprocess.align_supercells(supercells, rows, columns) == output_test


@pytest.mark.parametrize(("rows", "bbox", "output"), [([1.0], [0.0], [1.0])])
def test_align_rows(rows, bbox, output):
    assert postprocess.align_rows(rows, bbox) == output


@pytest.mark.parametrize(
    ("output_format", "expectation"),
    [
        ("html", "<tr><td>Blind</td><td>5</td><td>1</td><td>4</td><td>34.5%, n=1</td>"),
        (
            "cells",
            {
                "column_nums": [0],
                "row_nums": [2],
                "column header": False,
                "cell text": "Blind",
            },
        ),
        ("dataframe", ["Blind", "5", "1", "4", "34.5%, n=1", "1199 sec, n=1"]),
        (None, "<tr><td>Blind</td><td>5</td><td>1</td><td>4</td><td>34.5%, n=1</td>"),
    ],
)
def test_table_prediction_output_format(
    output_format,
    expectation,
    table_transformer,
    example_image,
    mocker,
    example_table_cells,
    mocked_ocr_tokens,
):
    mocker.patch.object(tables, "recognize", return_value=example_table_cells)
    mocker.patch.object(
        tables.UnstructuredTableTransformerModel,
        "get_structure",
        return_value=None,
    )
    if output_format:
        result = table_transformer.run_prediction(
            example_image,
            result_format=output_format,
            ocr_tokens=mocked_ocr_tokens,
        )
    else:
        result = table_transformer.run_prediction(example_image, ocr_tokens=mocked_ocr_tokens)

    if output_format == "dataframe":
        assert expectation in result.values
    elif output_format == "cells":
        # other output like bbox are flakey to test since they depend on OCR and it may change
        # slightly when OCR pacakge changes or even on different machines
        validation_fields = ("column_nums", "row_nums", "column header", "cell text")
        assert expectation in [{key: cell[key] for key in validation_fields} for cell in result]
    else:
        assert expectation in result


def test_table_prediction_output_format_when_wrong_type_then_value_error(
    table_transformer,
    example_image,
    mocker,
    example_table_cells,
    mocked_ocr_tokens,
):
    mocker.patch.object(tables, "recognize", return_value=example_table_cells)
    mocker.patch.object(
        tables.UnstructuredTableTransformerModel,
        "get_structure",
        return_value=None,
    )
    with pytest.raises(ValueError):
        table_transformer.run_prediction(
            example_image,
            result_format="Wrong format",
            ocr_tokens=mocked_ocr_tokens,
        )


def test_table_prediction_runs_with_empty_recognize(
    table_transformer,
    example_image,
    mocker,
    mocked_ocr_tokens,
):
    mocker.patch.object(tables, "recognize", return_value=[])
    mocker.patch.object(
        tables.UnstructuredTableTransformerModel,
        "get_structure",
        return_value=None,
    )
    assert table_transformer.run_prediction(example_image, ocr_tokens=mocked_ocr_tokens) == ""


def test_table_prediction_with_ocr_tokens(table_transformer, example_image, mocked_ocr_tokens):
    prediction = table_transformer.predict(example_image, ocr_tokens=mocked_ocr_tokens)
    assert '<table><thead><tr><th rowspan="2">' in prediction
    assert "<tr><td>Blind</td><td>5</td><td>1</td><td>4</td><td>34.5%, n=1</td>" in prediction


def test_table_prediction_with_no_ocr_tokens(table_transformer, example_image):
    with pytest.raises(ValueError):
        table_transformer.predict(example_image)


@pytest.mark.parametrize(
    ("thresholds", "expected_object_number"),
    [
        ({"0": 0.5}, 1),
        ({"0": 0.1}, 3),
        ({"0": 0.9}, 0),
    ],
)
def test_objects_are_filtered_based_on_class_thresholds_when_correct_prediction_and_threshold(
    thresholds,
    expected_object_number,
):
    objects = [
        {"label": "0", "score": 0.2},
        {"label": "0", "score": 0.4},
        {"label": "0", "score": 0.55},
    ]
    assert len(apply_thresholds_on_objects(objects, thresholds)) == expected_object_number


@pytest.mark.parametrize(
    ("thresholds", "expected_object_number"),
    [
        ({"0": 0.5, "1": 0.1}, 4),
        ({"0": 0.1, "1": 0.9}, 3),
        ({"0": 0.9, "1": 0.5}, 1),
    ],
)
def test_objects_are_filtered_based_on_class_thresholds_when_two_classes(
    thresholds,
    expected_object_number,
):
    objects = [
        {"label": "0", "score": 0.2},
        {"label": "0", "score": 0.4},
        {"label": "0", "score": 0.55},
        {"label": "1", "score": 0.2},
        {"label": "1", "score": 0.4},
        {"label": "1", "score": 0.55},
    ]
    assert len(apply_thresholds_on_objects(objects, thresholds)) == expected_object_number


def test_objects_filtering_when_missing_threshold():
    class_name = "class_name"
    objects = [{"label": class_name, "score": 0.2}]
    thresholds = {"1": 0.5}
    with pytest.raises(KeyError, match=class_name):
        apply_thresholds_on_objects(objects, thresholds)


def test_intersect():
    a = postprocess.Rect()
    b = postprocess.Rect([1, 2, 3, 4])
    assert a.intersect(b).get_area() == 4.0


def test_include_rect():
    a = postprocess.Rect()
    assert a.include_rect([1, 2, 3, 4]).get_area() == 4.0


@pytest.mark.parametrize(
    ("spans", "join_with_space", "expected"),
    [
        (
            [
                {
                    "flags": 2**0,
                    "text": "5",
                    "superscript": False,
                    "span_num": 0,
                    "line_num": 0,
                    "block_num": 0,
                },
            ],
            True,
            "",
        ),
        (
            [
                {
                    "flags": 2**0,
                    "text": "p",
                    "superscript": False,
                    "span_num": 0,
                    "line_num": 0,
                    "block_num": 0,
                },
            ],
            True,
            "p",
        ),
        (
            [
                {
                    "flags": 2**0,
                    "text": "p",
                    "superscript": False,
                    "span_num": 0,
                    "line_num": 0,
                    "block_num": 0,
                },
                {
                    "flags": 2**0,
                    "text": "p",
                    "superscript": False,
                    "span_num": 0,
                    "line_num": 0,
                    "block_num": 0,
                },
            ],
            True,
            "p p",
        ),
        (
            [
                {
                    "flags": 2**0,
                    "text": "p",
                    "superscript": False,
                    "span_num": 0,
                    "line_num": 0,
                    "block_num": 0,
                },
                {
                    "flags": 2**0,
                    "text": "p",
                    "superscript": False,
                    "span_num": 0,
                    "line_num": 0,
                    "block_num": 1,
                },
            ],
            True,
            "p p",
        ),
        (
            [
                {
                    "flags": 2**0,
                    "text": "p",
                    "superscript": False,
                    "span_num": 0,
                    "line_num": 0,
                    "block_num": 0,
                },
                {
                    "flags": 2**0,
                    "text": "p",
                    "superscript": False,
                    "span_num": 0,
                    "line_num": 0,
                    "block_num": 1,
                },
            ],
            False,
            "p p",
        ),
    ],
)
def test_extract_text_from_spans(spans, join_with_space, expected):
    res = postprocess.extract_text_from_spans(
        spans,
        join_with_space=join_with_space,
        remove_integer_superscripts=True,
    )
    assert res == expected


@pytest.mark.parametrize(
    ("supercells", "expected_len"),
    [
        ([{"header": "hi", "row_numbers": [0, 1, 2], "score": 0.9}], 1),
        (
            [
                {
                    "header": "hi",
                    "row_numbers": [0],
                    "column_numbers": [1, 2, 3],
                    "score": 0.9,
                },
                {
                    "header": "hi",
                    "row_numbers": [1],
                    "column_numbers": [1],
                    "score": 0.9,
                },
                {
                    "header": "hi",
                    "row_numbers": [1],
                    "column_numbers": [2],
                    "score": 0.9,
                },
                {
                    "header": "hi",
                    "row_numbers": [1],
                    "column_numbers": [3],
                    "score": 0.9,
                },
            ],
            4,
        ),
        (
            [
                {
                    "header": "hi",
                    "row_numbers": [0],
                    "column_numbers": [0],
                    "score": 0.9,
                },
                {
                    "header": "hi",
                    "row_numbers": [1],
                    "column_numbers": [0],
                    "score": 0.9,
                },
                {
                    "header": "hi",
                    "row_numbers": [1, 2],
                    "column_numbers": [0],
                    "score": 0.9,
                },
                {
                    "header": "hi",
                    "row_numbers": [3],
                    "column_numbers": [0],
                    "score": 0.9,
                },
            ],
            3,
        ),
    ],
)
def test_header_supercell_tree(supercells, expected_len):
    postprocess.header_supercell_tree(supercells)
    assert len(supercells) == expected_len


@pytest.mark.parametrize("zoom", [1, 0.1, 5, -1, 0])
def test_zoom_image(example_image, zoom):
    width, height = example_image.size
    new_image = tables.zoom_image(example_image, zoom)
    new_w, new_h = new_image.size
    if zoom <= 0:
        zoom = 1
    assert new_w == np.round(width * zoom, 0)
    assert new_h == np.round(height * zoom, 0)


@pytest.mark.parametrize(
    ("input_cells", "expected_html"),
    [
        # +----------+---------------------+
        # | row1col1 | row1col2 | row1col3 |
        # |----------|----------+----------|
        # | row2col1 | row2col2 | row2col3 |
        # +----------+----------+----------+
        pytest.param(
            [
                {
                    "row_nums": [0],
                    "column_nums": [0],
                    "cell text": "row1col1",
                    "column header": False,
                },
                {
                    "row_nums": [0],
                    "column_nums": [1],
                    "cell text": "row1col2",
                    "column header": False,
                },
                {
                    "row_nums": [0],
                    "column_nums": [2],
                    "cell text": "row1col3",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [0],
                    "cell text": "row2col1",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [1],
                    "cell text": "row2col2",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [2],
                    "cell text": "row2col3",
                    "column header": False,
                },
            ],
            (
                "<table><tbody><tr><td>row1col1</td><td>row1col2</td><td>row1col3</td></tr>"
                "<tr><td>row2col1</td><td>row2col2</td><td>row2col3</td></tr></tbody></table>"
            ),
            id="simple table without header",
        ),
        # +----------+---------------------+
        # |  h1col1  |  h1col2  |  h1col3  |
        # |----------|----------+----------|
        # | row1col1 | row1col2 | row1col3 |
        # |----------|----------+----------|
        # | row2col1 | row2col2 | row2col3 |
        # +----------+----------+----------+
        pytest.param(
            [
                {"row_nums": [0], "column_nums": [0], "cell text": "h1col1", "column header": True},
                {"row_nums": [0], "column_nums": [1], "cell text": "h1col2", "column header": True},
                {"row_nums": [0], "column_nums": [2], "cell text": "h1col2", "column header": True},
                {
                    "row_nums": [1],
                    "column_nums": [0],
                    "cell text": "row1col1",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [1],
                    "cell text": "row1col2",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [2],
                    "cell text": "row1col3",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [0],
                    "cell text": "row2col1",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [1],
                    "cell text": "row2col2",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [2],
                    "cell text": "row2col3",
                    "column header": False,
                },
            ],
            (
                "<table><thead><tr><th>h1col1</th><th>h1col2</th><th>h1col2</th></tr></thead>"
                "<tbody><tr><td>row1col1</td><td>row1col2</td><td>row1col3</td></tr>"
                "<tr><td>row2col1</td><td>row2col2</td><td>row2col3</td></tr></tbody></table>"
            ),
            id="simple table with header",
        ),
        # +----------+---------------------+
        # |  h1col1  |  h1col2  |  h1col3  |
        # |----------|----------+----------|
        # | row1col1 | row1col2 | row1col3 |
        # |----------|----------+----------|
        # | row2col1 | row2col2 | row2col3 |
        # +----------+----------+----------+
        pytest.param(
            [
                {"row_nums": [0], "column_nums": [1], "cell text": "h1col2", "column header": True},
                {
                    "row_nums": [2],
                    "column_nums": [0],
                    "cell text": "row2col1",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [0],
                    "cell text": "row1col1",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [1],
                    "cell text": "row2col2",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [1],
                    "cell text": "row1col2",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [2],
                    "cell text": "row2col3",
                    "column header": False,
                },
                {"row_nums": [0], "column_nums": [0], "cell text": "h1col1", "column header": True},
                {
                    "row_nums": [1],
                    "column_nums": [2],
                    "cell text": "row1col3",
                    "column header": False,
                },
                {"row_nums": [0], "column_nums": [2], "cell text": "h1col2", "column header": True},
            ],
            (
                "<table><thead><tr><th>h1col1</th><th>h1col2</th><th>h1col2</th></tr></thead>"
                "<tbody><tr><td>row1col1</td><td>row1col2</td><td>row1col3</td></tr>"
                "<tr><td>row2col1</td><td>row2col2</td><td>row2col3</td></tr></tbody></table>"
            ),
            id="simple table with header, mixed elements",
        ),
        # +----------+---------------------+
        # |    two   |   two columns       |
        # |          |----------+----------|
        # |    rows  |sub cell 1|sub cell 2|
        # +----------+----------+----------+
        pytest.param(
            [
                {
                    "row_nums": [0, 1],
                    "column_nums": [0],
                    "cell text": "two row",
                    "column header": False,
                },
                {
                    "row_nums": [0],
                    "column_nums": [1, 2],
                    "cell text": "two cols",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [1],
                    "cell text": "sub cell 1",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [2],
                    "cell text": "sub cell 2",
                    "column header": False,
                },
            ],
            (
                '<table><tbody><tr><td rowspan="2">two row</td><td colspan="2">two '
                "cols</td></tr><tr><td>sub cell 1</td><td>sub cell 2</td></tr>"
                "</tbody></table>"
            ),
            id="various spans, no headers",
        ),
        # +----------+---------------------+----------+
        # |          |       h1col23       |  h1col4  |
        # | h12col1  |----------+----------+----------|
        # |          |  h2col2  |       h2col34       |
        # |----------|----------+----------+----------+
        # |  r3col1  |  r3col2  |                     |
        # |----------+----------|      r34col34       |
        # |       r4col12       |                     |
        # +----------+----------+----------+----------+
        pytest.param(
            [
                {
                    "row_nums": [0, 1],
                    "column_nums": [0],
                    "cell text": "h12col1",
                    "column header": True,
                },
                {
                    "row_nums": [0],
                    "column_nums": [1, 2],
                    "cell text": "h1col23",
                    "column header": True,
                },
                {"row_nums": [0], "column_nums": [3], "cell text": "h1col4", "column header": True},
                {"row_nums": [1], "column_nums": [1], "cell text": "h2col2", "column header": True},
                {
                    "row_nums": [1],
                    "column_nums": [2, 3],
                    "cell text": "h2col34",
                    "column header": True,
                },
                {
                    "row_nums": [2],
                    "column_nums": [0],
                    "cell text": "r3col1",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [1],
                    "cell text": "r3col2",
                    "column header": False,
                },
                {
                    "row_nums": [2, 3],
                    "column_nums": [2, 3],
                    "cell text": "r34col34",
                    "column header": False,
                },
                {
                    "row_nums": [3],
                    "column_nums": [0, 1],
                    "cell text": "r4col12",
                    "column header": False,
                },
            ],
            (
                '<table><thead><tr><th rowspan="2">h12col1</th>'
                '<th colspan="2">h1col23</th><th>h1col4</th></tr>'
                '<tr><th>h2col2</th><th colspan="2">h2col34</th></tr></thead><tbody>'
                '<tr><td>r3col1</td><td>r3col2</td><td colspan="2" rowspan="2">r34col34</td></tr>'
                '<tr><td colspan="2">r4col12</td></tr></tbody></table>'
            ),
            id="various spans, with 2 row header",
        ),
    ],
)
def test_cells_to_html(input_cells, expected_html):
    assert tables.cells_to_html(input_cells) == expected_html


@pytest.mark.parametrize(
    ("input_cells", "expected_cells"),
    [
        pytest.param(
            [
                {"row_nums": [0], "column_nums": [0], "cell text": "h1col1", "column header": True},
                {"row_nums": [0], "column_nums": [1], "cell text": "h1col2", "column header": True},
                {"row_nums": [0], "column_nums": [2], "cell text": "h1col2", "column header": True},
                {
                    "row_nums": [1],
                    "column_nums": [0],
                    "cell text": "row1col1",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [1],
                    "cell text": "row1col2",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [2],
                    "cell text": "row1col3",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [0],
                    "cell text": "row2col1",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [1],
                    "cell text": "row2col2",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [2],
                    "cell text": "row2col3",
                    "column header": False,
                },
            ],
            [
                {"row_nums": [0], "column_nums": [0], "cell text": "h1col1", "column header": True},
                {"row_nums": [0], "column_nums": [1], "cell text": "h1col2", "column header": True},
                {"row_nums": [0], "column_nums": [2], "cell text": "h1col2", "column header": True},
                {
                    "row_nums": [1],
                    "column_nums": [0],
                    "cell text": "row1col1",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [1],
                    "cell text": "row1col2",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [2],
                    "cell text": "row1col3",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [0],
                    "cell text": "row2col1",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [1],
                    "cell text": "row2col2",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [2],
                    "cell text": "row2col3",
                    "column header": False,
                },
            ],
            id="identical tables, no changes expected",
        ),
        pytest.param(
            [
                {"row_nums": [0], "column_nums": [0], "cell text": "h1col1", "column header": True},
                {"row_nums": [0], "column_nums": [2], "cell text": "h1col2", "column header": True},
                {
                    "row_nums": [1],
                    "column_nums": [0],
                    "cell text": "row1col1",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [1],
                    "cell text": "row1col2",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [0],
                    "cell text": "row2col1",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [1],
                    "cell text": "row2col2",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [2],
                    "cell text": "row2col3",
                    "column header": False,
                },
            ],
            [
                {"row_nums": [0], "column_nums": [0], "cell text": "h1col1", "column header": True},
                {"row_nums": [0], "column_nums": [1], "cell text": "", "column header": True},
                {"row_nums": [0], "column_nums": [2], "cell text": "h1col2", "column header": True},
                {
                    "row_nums": [1],
                    "column_nums": [0],
                    "cell text": "row1col1",
                    "column header": False,
                },
                {
                    "row_nums": [1],
                    "column_nums": [1],
                    "cell text": "row1col2",
                    "column header": False,
                },
                {"row_nums": [1], "column_nums": [2], "cell text": "", "column header": False},
                {
                    "row_nums": [2],
                    "column_nums": [0],
                    "cell text": "row2col1",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [1],
                    "cell text": "row2col2",
                    "column header": False,
                },
                {
                    "row_nums": [2],
                    "column_nums": [2],
                    "cell text": "row2col3",
                    "column header": False,
                },
            ],
            id="missing column in header and in the middle",
        ),
        pytest.param(
            [
                {
                    "row_nums": [0, 1],
                    "column_nums": [0],
                    "cell text": "h12col1",
                    "column header": True,
                },
                {
                    "row_nums": [0],
                    "column_nums": [1, 2],
                    "cell text": "h1col23",
                    "column header": True,
                },
                {"row_nums": [1], "column_nums": [1], "cell text": "h2col2", "column header": True},
                {
                    "row_nums": [1],
                    "column_nums": [2, 3],
                    "cell text": "h2col34",
                    "column header": True,
                },
                {
                    "row_nums": [2],
                    "column_nums": [0],
                    "cell text": "r3col1",
                    "column header": False,
                },
                {
                    "row_nums": [2, 3],
                    "column_nums": [2, 3],
                    "cell text": "r34col34",
                    "column header": False,
                },
                {
                    "row_nums": [3],
                    "column_nums": [0, 1],
                    "cell text": "r4col12",
                    "column header": False,
                },
            ],
            [
                {
                    "row_nums": [0, 1],
                    "column_nums": [0],
                    "cell text": "h12col1",
                    "column header": True,
                },
                {
                    "row_nums": [0],
                    "column_nums": [1, 2],
                    "cell text": "h1col23",
                    "column header": True,
                },
                {"row_nums": [0], "column_nums": [3], "cell text": "", "column header": True},
                {"row_nums": [1], "column_nums": [1], "cell text": "h2col2", "column header": True},
                {
                    "row_nums": [1],
                    "column_nums": [2, 3],
                    "cell text": "h2col34",
                    "column header": True,
                },
                {
                    "row_nums": [2],
                    "column_nums": [0],
                    "cell text": "r3col1",
                    "column header": False,
                },
                {"row_nums": [2], "column_nums": [1], "cell text": "", "column header": False},
                {
                    "row_nums": [2, 3],
                    "column_nums": [2, 3],
                    "cell text": "r34col34",
                    "column header": False,
                },
                {
                    "row_nums": [3],
                    "column_nums": [0, 1],
                    "cell text": "r4col12",
                    "column header": False,
                },
            ],
            id="missing column in header and in the middle in table with spans",
        ),
    ],
)
def test_fill_cells(input_cells, expected_cells):
    def sort_cells(cells):
        return sorted(cells, key=lambda x: (x["row_nums"], x["column_nums"]))

    assert sort_cells(tables.fill_cells(input_cells)) == sort_cells(expected_cells)


def test_padded_results_has_right_dimensions(table_transformer, example_image):
    str_class_name2idx = tables.get_class_map("structure")
    # a simpler mapping so we keep all structure in the returned objs below for test
    str_class_idx2name = dict.fromkeys(str_class_name2idx.values(), "table cell")
    # pad size is no more than 10% of the original image so we can setup test below easier
    pad = int(min(example_image.size) / 10)

    structure = table_transformer.get_structure(example_image, pad_for_structure_detection=pad)
    # boxes deteced OUTSIDE of the original image; this shouldn't happen but we want to make sure
    # the code handles it as expected
    structure["pred_boxes"][0][0, :2] = 0.5
    structure["pred_boxes"][0][0, 2:] = 1.0
    # mock a box we know are safly inside the original image with known positions
    width, height = example_image.size
    padded_width = width + pad * 2
    padded_height = height + pad * 2
    original = [1, 3, 101, 53]
    structure["pred_boxes"][0][1, :] = torch.tensor(
        [
            (51 + pad) / padded_width,
            (28 + pad) / padded_height,
            100 / padded_width,
            50 / padded_height,
        ],
    )
    objs = tables.outputs_to_objects(structure, example_image.size, str_class_idx2name)
    np.testing.assert_almost_equal(objs[0]["bbox"], [-pad, -pad, width + pad, height + pad], 4)
    np.testing.assert_almost_equal(objs[1]["bbox"], original, 4)
    # a more strict test would be to constrain the actual detected boxes to be within the original
    # image but that requires the table transformer to behave in certain ways and do not
    # actually test the padding math; so here we use the relaxed condition
    for obj in objs[2:]:
        x1, y1, x2, y2 = obj["bbox"]
        assert max(x1, x2) < width + pad
        assert max(y1, y2) < height + pad


def test_compute_confidence_score_zero_division_error_handling():
    assert tables.compute_confidence_score([]) == 0


@pytest.mark.parametrize(
    ("column_span_score", "row_span_score", "expected_text_to_indexes"),
    [
        (
            0.9,
            0.8,
            (
                {
                    "one three": {"row_nums": [0, 1], "column_nums": [0]},
                    "two": {"row_nums": [0], "column_nums": [1]},
                    "four": {"row_nums": [1], "column_nums": [1]},
                }
            ),
        ),
        (
            0.8,
            0.9,
            (
                {
                    "one two": {"row_nums": [0], "column_nums": [0, 1]},
                    "three": {"row_nums": [1], "column_nums": [0]},
                    "four": {"row_nums": [1], "column_nums": [1]},
                }
            ),
        ),
    ],
)
def test_subcells_filtering_when_overlapping_spanning_cells(
    column_span_score,
    row_span_score,
    expected_text_to_indexes,
):
    """
    # table
    # +-----------+----------+
    # |    one    |   two    |
    # |-----------+----------|
    # |    three  |   four   |
    # +-----------+----------+

    spanning cells over first row and over first column
    """
    table_structure = {
        "rows": [
            {"bbox": [0, 0, 10, 20]},
            {"bbox": [10, 0, 20, 20]},
        ],
        "columns": [
            {"bbox": [0, 0, 20, 10]},
            {"bbox": [0, 10, 20, 20]},
        ],
        "spanning cells": [
            {"bbox": [0, 0, 20, 10], "score": column_span_score},
            {"bbox": [0, 0, 10, 20], "score": row_span_score},
        ],
    }
    tokens = [
        {
            "text": "one",
            "bbox": [0, 0, 10, 10],
        },
        {
            "text": "two",
            "bbox": [0, 10, 10, 20],
        },
        {
            "text": "three",
            "bbox": [10, 0, 20, 10],
        },
        {"text": "four", "bbox": [10, 10, 20, 20]},
    ]
    token_args = {"span_num": 1, "line_num": 1, "block_num": 1}
    for token in tokens:
        token.update(token_args)
    for spanning_cell in table_structure["spanning cells"]:
        spanning_cell["projected row header"] = False

    # table structure is edited inside structure_to_cells, save copy for future runs
    saved_table_structure = deepcopy(table_structure)

    predicted_cells, _ = structure_to_cells(table_structure, tokens=tokens)
    predicted_text_to_indexes = {
        cell["cell text"]: {
            "row_nums": cell["row_nums"],
            "column_nums": cell["column_nums"],
        }
        for cell in predicted_cells
    }
    assert predicted_text_to_indexes == expected_text_to_indexes

    # swap spanning cells to ensure the highest prob spanning cell is used
    spans = saved_table_structure["spanning cells"]
    spans[0], spans[1] = spans[1], spans[0]
    saved_table_structure["spanning cells"] = spans

    predicted_cells_after_reorder, _ = structure_to_cells(saved_table_structure, tokens=tokens)
    assert predicted_cells_after_reorder == predicted_cells


def test_model_init_is_thread_safe():
    threads = []
    tables.tables_agent.model = None
    for i in range(5):
        thread = threading.Thread(target=tables.load_agent)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    assert tables.tables_agent.model is not None
