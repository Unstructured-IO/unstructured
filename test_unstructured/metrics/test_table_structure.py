import pytest

from unstructured.metrics.table_structure import (
    eval_table_transformer_for_file,
    image_or_pdf_to_dataframe,
)


@pytest.mark.parametrize(
    "filename",
    [
        "example-docs/table-multi-row-column-cells.png",
        "example-docs/table-multi-row-column-cells.pdf",
    ],
)
def test_image_or_pdf_to_dataframe(filename):
    df = image_or_pdf_to_dataframe(filename)
    assert ["Blind", "5", "1", "4", "34.5%, n=1", "1199 sec, n=1"] in df.values


def test_eval_table_transformer_for_file():
    score = eval_table_transformer_for_file(
        "example-docs/table-multi-row-column-cells.png",
        "example-docs/table-multi-row-column-cells-actual.csv",
    )
    # avoid severe degradation of performance
    assert 0.8 < score < 1
