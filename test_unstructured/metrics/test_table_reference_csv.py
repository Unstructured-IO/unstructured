"""Evaluate the CSV cell text without changing reference labels or blank cells."""

import csv

import numpy as np
import pandas as pd
import pytest

from unstructured.metrics import table_structure


@pytest.mark.parametrize("eval_func", ["ratio", "token_ratio"])
@pytest.mark.parametrize(
    "cells",
    [
        ["alpha", "", "omega"],
        ["007", "010", "000"],
        ["NA", "N/A", "NULL"],
        ["None", "nan", "NaN"],
        ["12.00", "1e3", "-0"],
        ["9007199254740993", "0.00001", "42"],
        ["alpha", "beta", "omega"],
        ["quoted, value", "two\nlines", "café"],
    ],
)
def test_exact_predicted_cell_text_scores_as_an_exact_reference_match(
    cells, eval_func, tmp_path, monkeypatch
):
    reference_path = tmp_path / "reference.csv"
    with reference_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["a", "b", "c"])
        writer.writerow(cells)
    predicted = pd.DataFrame([cells], columns=["a", "b", "c"])
    before = predicted.copy(deep=True)
    monkeypatch.setattr(table_structure, "image_or_pdf_to_dataframe", lambda _: predicted)

    score = table_structure.eval_table_transformer_for_file(
        "unused-model-input.png", str(reference_path), eval_func=eval_func
    )

    assert score == pytest.approx(1.0)
    pd.testing.assert_frame_equal(predicted, before)


def test_missing_prediction_values_match_blank_reference_cells(tmp_path, monkeypatch):
    reference_path = tmp_path / "reference.csv"
    reference_path.write_text("a,b,c\nalpha,,omega\n", encoding="utf-8")
    predicted = pd.DataFrame([["alpha", np.nan, "omega"]], columns=["a", "b", "c"])
    monkeypatch.setattr(table_structure, "image_or_pdf_to_dataframe", lambda _: predicted)

    score = table_structure.eval_table_transformer_for_file(
        "unused-model-input.png", str(reference_path), eval_func="ratio"
    )

    assert score == pytest.approx(1.0)
    assert pd.isna(predicted.iloc[0, 1])


def test_incorrect_cell_text_is_still_penalized(tmp_path, monkeypatch):
    reference_path = tmp_path / "reference.csv"
    reference_path.write_text("a,b,c\nalpha,beta,omega\n", encoding="utf-8")
    monkeypatch.setattr(
        table_structure,
        "image_or_pdf_to_dataframe",
        lambda _: pd.DataFrame([["alpha", "incorrect", "omega"]]),
    )

    score = table_structure.eval_table_transformer_for_file(
        "unused-model-input.png", str(reference_path), eval_func="ratio"
    )

    assert 0 < score < 1
