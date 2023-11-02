import os
import pathlib

from unstructured.metrics.evaluate import (
    measure_text_edit_distance,
)

DIRECTORY = pathlib.Path(__file__).parent.resolve()
TESTING_FILE_DIR = os.path.join(DIRECTORY, "test_evaluate_files")

UNSTRUCTURED_OUTPUT_DIRNAME = "unstructured_output"
GOLD_CCT_DIRNAME = "gold_standard_cct"


def test_text_extraction_takes_list():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    output_list = ["currency.csv.json"]
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    measure_text_edit_distance(
        output_dir=output_dir,
        output_list=output_list,
        source_dir=source_dir,
        export_dir="test_evaluate_results",
    )
