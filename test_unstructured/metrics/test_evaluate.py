import os
import pathlib

import pandas as pd
import pytest

from unstructured.metrics.evaluate import (
    measure_text_edit_distance,
)

is_in_docker = os.path.exists("/.dockerenv")

EXAMPLE_DOCS_DIRECTORY = os.path.join(
    pathlib.Path(__file__).parent.resolve(), "..", "..", "example-docs"
)
TESTING_FILE_DIR = os.path.join(EXAMPLE_DOCS_DIRECTORY, "test_evaluate_files")

UNSTRUCTURED_OUTPUT_DIRNAME = "unstructured_output"
GOLD_CCT_DIRNAME = "gold_standard_cct"


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_text_extraction_takes_list():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    output_list = ["currency.csv.json"]
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")
    measure_text_edit_distance(
        output_dir=output_dir,
        source_dir=source_dir,
        output_list=output_list,
        export_dir=export_dir,
    )
    # check that only the listed files are included
    with open(os.path.join(export_dir, "all-docs-cct.tsv")) as f:
        lines = f.read().splitlines()
    assert len(lines) == len(output_list) + 1  # includes header


def test_text_extraction_grouping():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")
    measure_text_edit_distance(
        output_dir=output_dir, source_dir=source_dir, export_dir=export_dir, grouping="doctype"
    )
    df = pd.read_csv(os.path.join(export_dir, "all-doctype-agg-cct.tsv"), sep="\t")
    assert len(df) == 4
