import os
import pathlib
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from unstructured.metrics.evaluate import (
    ElementTypeMetricsCalculator,
    TableStructureMetricsCalculator,
    TextExtractionMetricsCalculator,
    filter_metrics,
    get_mean_grouping,
)

is_in_docker = os.path.exists("/.dockerenv")

EXAMPLE_DOCS_DIRECTORY = os.path.join(
    pathlib.Path(__file__).parent.resolve(), "..", "..", "example-docs"
)
TESTING_FILE_DIR = os.path.join(EXAMPLE_DOCS_DIRECTORY, "test_evaluate_files")

UNSTRUCTURED_OUTPUT_DIRNAME = "unstructured_output"
GOLD_CCT_DIRNAME = "gold_standard_cct"
GOLD_ELEMENT_TYPE_DIRNAME = "gold_standard_element_type"
GOLD_TABLE_STRUCTURE_DIRNAME = "gold_standard_table_structure"
UNSTRUCTURED_CCT_DIRNAME = "unstructured_output_cct"
UNSTRUCTURED_TABLE_STRUCTURE_DIRNAME = "unstructured_output_table_structure"

DUMMY_DF_CCT = pd.DataFrame(
    {
        "filename": [
            "Bank Good Credit Loan.pptx",
            "Performance-Audit-Discussion.pdf",
            "currency.csv",
        ],
        "doctype": ["pptx", "pdf", "csv"],
        "connector": ["connector1", "connector1", "connector2"],
        "cct-accuracy": [0.812, 0.994, 0.887],
        "cct-%missing": [0.001, 0.002, 0.041],
    }
)

DUMMY_DF_ELEMENT_TYPE = pd.DataFrame(
    {
        "filename": [
            "Bank Good Credit Loan.pptx",
            "Performance-Audit-Discussion.pdf",
            "currency.csv",
        ],
        "doctype": ["pptx", "pdf", "csv"],
        "connector": ["connector1", "connector1", "connector2"],
        "element-type-accuracy": [0.812, 0.994, 0.887],
    }
)


@pytest.fixture()
def _cleanup_after_test():
    """Fixture for removing side-effects of running tests in this file."""

    def remove_generated_directories():
        """Remove directories created from running tests."""

        # Directories to be removed:
        target_dir_names = [
            "test_evaluate_results_cct",
            "test_evaluate_results_cct_txt",
            "test_evaluate_results_element_type",
            "test_evaluate_result_table_structure",
        ]
        subdirs = (d for d in os.scandir(TESTING_FILE_DIR) if d.is_dir())
        for d in subdirs:
            if d.name in target_dir_names:
                shutil.rmtree(d.path)

    # Run test as normal
    yield
    remove_generated_directories()


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_text_extraction_evaluation():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")

    TextExtractionMetricsCalculator(
        documents_dir=output_dir, ground_truths_dir=source_dir
    ).calculate(export_dir=export_dir, visualize_progress=False, display_agg_df=False)

    assert os.path.isfile(os.path.join(export_dir, "all-docs-cct.tsv"))
    df = pd.read_csv(os.path.join(export_dir, "all-docs-cct.tsv"), sep="\t")
    assert len(df) == 3
    assert len(df.columns) == 5
    assert df.iloc[0].filename == "Bank Good Credit Loan.pptx"


@pytest.mark.parametrize(
    ("calculator_class", "output_dirname", "source_dirname", "path", "expected_length", "kwargs"),
    [
        (
            TextExtractionMetricsCalculator,
            UNSTRUCTURED_CCT_DIRNAME,
            GOLD_CCT_DIRNAME,
            Path("Bank Good Credit Loan.pptx.txt"),
            5,
            {"document_type": "txt"},
        ),
        (
            TableStructureMetricsCalculator,
            UNSTRUCTURED_TABLE_STRUCTURE_DIRNAME,
            GOLD_TABLE_STRUCTURE_DIRNAME,
            Path("IRS-2023-Form-1095-A.pdf.json"),
            13,
            {},
        ),
        (
            ElementTypeMetricsCalculator,
            UNSTRUCTURED_OUTPUT_DIRNAME,
            GOLD_ELEMENT_TYPE_DIRNAME,
            Path("IRS-form-1987.pdf.json"),
            4,
            {},
        ),
    ],
)
def test_process_document_returns_the_correct_amount_of_values(
    calculator_class, output_dirname, source_dirname, path, expected_length, kwargs
):
    output_dir = Path(TESTING_FILE_DIR) / output_dirname
    source_dir = Path(TESTING_FILE_DIR) / source_dirname

    calculator = calculator_class(documents_dir=output_dir, ground_truths_dir=source_dir, **kwargs)
    output_list = calculator._process_document(path)
    assert len(output_list) == expected_length


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_text_extraction_evaluation_type_txt():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_CCT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")

    TextExtractionMetricsCalculator(
        documents_dir=output_dir, ground_truths_dir=source_dir, document_type="txt"
    ).calculate(export_dir=export_dir)

    df = pd.read_csv(os.path.join(export_dir, "all-docs-cct.tsv"), sep="\t")
    assert len(df) == 3
    assert len(df.columns) == 5
    assert df.iloc[0].filename == "Bank Good Credit Loan.pptx"


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_element_type_evaluation():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_ELEMENT_TYPE_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")

    ElementTypeMetricsCalculator(
        documents_dir=output_dir,
        ground_truths_dir=source_dir,
    ).calculate(export_dir=export_dir, visualize_progress=False)

    assert os.path.isfile(os.path.join(export_dir, "all-docs-element-type-frequency.tsv"))
    df = pd.read_csv(os.path.join(export_dir, "all-docs-element-type-frequency.tsv"), sep="\t")
    assert len(df) == 1
    assert len(df.columns) == 4
    assert df.iloc[0].filename == "IRS-form-1987.pdf"


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_table_structure_evaluation():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_TABLE_STRUCTURE_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_TABLE_STRUCTURE_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_result_table_structure")

    TableStructureMetricsCalculator(
        documents_dir=output_dir,
        ground_truths_dir=source_dir,
    ).calculate(export_dir=export_dir, visualize_progress=False)

    assert os.path.isfile(os.path.join(export_dir, "all-docs-table-structure-accuracy.tsv"))
    assert os.path.isfile(os.path.join(export_dir, "aggregate-table-structure-accuracy.tsv"))
    df = pd.read_csv(os.path.join(export_dir, "all-docs-table-structure-accuracy.tsv"), sep="\t")
    assert len(df) == 1
    assert len(df.columns) == 13
    assert df.iloc[0].filename == "IRS-2023-Form-1095-A.pdf"


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_text_extraction_takes_list():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    output_list = ["currency.csv.json"]
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")

    TextExtractionMetricsCalculator(
        documents_dir=output_dir,
        ground_truths_dir=source_dir,
    ).on_files(document_paths=output_list).calculate(export_dir=export_dir)

    # check that only the listed files are included
    assert os.path.isfile(os.path.join(export_dir, "all-docs-cct.tsv"))
    df = pd.read_csv(os.path.join(export_dir, "all-docs-cct.tsv"), sep="\t")
    assert len(df) == len(output_list)


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_text_extraction_with_grouping():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")

    TextExtractionMetricsCalculator(
        documents_dir=output_dir,
        ground_truths_dir=source_dir,
        group_by="doctype",
    ).calculate(export_dir=export_dir)

    df = pd.read_csv(os.path.join(export_dir, "all-doctype-agg-cct.tsv"), sep="\t")
    assert len(df) == 4  # metrics row and doctype rows


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_text_extraction_wrong_type():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")
    with pytest.raises(ValueError):
        TextExtractionMetricsCalculator(
            documents_dir=output_dir, ground_truths_dir=source_dir, document_type="invalid type"
        ).calculate(export_dir=export_dir)


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
@pytest.mark.parametrize(("grouping", "count_row"), [("doctype", 3), ("connector", 2)])
def test_get_mean_grouping_df_input(grouping: str, count_row: int):
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")
    get_mean_grouping(
        group_by=grouping,
        data_input=DUMMY_DF_CCT,
        export_dir=export_dir,
        eval_name="text_extraction",
    )
    grouped_df = pd.read_csv(os.path.join(export_dir, f"all-{grouping}-agg-cct.tsv"), sep="\t")
    assert grouped_df[grouping].dropna().nunique() == count_row


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_get_mean_grouping_tsv_input():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")

    TextExtractionMetricsCalculator(
        documents_dir=output_dir,
        ground_truths_dir=source_dir,
    ).calculate(export_dir=export_dir)

    filename = os.path.join(export_dir, "all-docs-cct.tsv")
    get_mean_grouping(
        group_by="doctype",
        data_input=filename,
        export_dir=export_dir,
        eval_name="text_extraction",
    )
    grouped_df = pd.read_csv(os.path.join(export_dir, "all-doctype-agg-cct.tsv"), sep="\t")
    assert grouped_df["doctype"].dropna().nunique() == 3


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_get_mean_grouping_invalid_group():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")

    TextExtractionMetricsCalculator(
        documents_dir=output_dir,
        ground_truths_dir=source_dir,
    ).calculate(export_dir=export_dir)

    df = pd.read_csv(os.path.join(export_dir, "all-docs-cct.tsv"), sep="\t")
    with pytest.raises(ValueError):
        get_mean_grouping(
            group_by="invalid",
            data_input=df,
            export_dir=export_dir,
            eval_name="text_extraction",
        )


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_text_extraction_grouping_empty_df():
    empty_df = pd.DataFrame()
    with pytest.raises(SystemExit):
        get_mean_grouping("doctype", empty_df, "some_dir", eval_name="text_extraction")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_get_mean_grouping_missing_grouping_column():
    df_with_no_grouping = pd.DataFrame({"some_column": [1, 2, 3]})
    with pytest.raises(SystemExit):
        get_mean_grouping("doctype", df_with_no_grouping, "some_dir", "text_extraction")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_get_mean_grouping_all_null_grouping_column():
    df_with_null_grouping = pd.DataFrame({"doctype": [None, None, None]})
    with pytest.raises(SystemExit):
        get_mean_grouping("doctype", df_with_null_grouping, "some_dir", eval_name="text_extraction")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_get_mean_grouping_invalid_eval_name():
    with pytest.raises(ValueError):
        get_mean_grouping("doctype", DUMMY_DF_ELEMENT_TYPE, "some_dir", eval_name="invalid")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
@pytest.mark.parametrize(("group_by", "count_row"), [("doctype", 3), ("connector", 2)])
def test_get_mean_grouping_element_type(group_by: str, count_row: int):
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_element_type")
    get_mean_grouping(
        group_by=group_by,
        data_input=DUMMY_DF_ELEMENT_TYPE,
        export_dir=export_dir,
        eval_name="element_type",
    )
    grouped_df = pd.read_csv(
        os.path.join(export_dir, f"all-{group_by}-agg-element-type.tsv"), sep="\t"
    )
    assert grouped_df[group_by].dropna().nunique() == count_row


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_filter_metrics():
    with open(os.path.join(TESTING_FILE_DIR, "filter_list.txt"), "w") as file:
        file.write("Bank Good Credit Loan.pptx\n")
        file.write("Performance-Audit-Discussion.pdf\n")
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")

    filter_metrics(
        data_input=DUMMY_DF_CCT,
        filter_list=os.path.join(TESTING_FILE_DIR, "filter_list.txt"),
        filter_by="filename",
        export_filename="filtered_metrics.tsv",
        export_dir=export_dir,
        return_type="file",
    )
    filtered_df = pd.read_csv(os.path.join(export_dir, "filtered_metrics.tsv"), sep="\t")
    assert len(filtered_df) == 2
    assert filtered_df["filename"].iloc[0] == "Bank Good Credit Loan.pptx"


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_get_mean_grouping_all_file():
    with open(os.path.join(TESTING_FILE_DIR, "filter_list.txt"), "w") as file:
        file.write("Bank Good Credit Loan.pptx\n")
        file.write("Performance-Audit-Discussion.pdf\n")
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")

    filter_metrics(
        data_input=DUMMY_DF_CCT,
        filter_list=["Bank Good Credit Loan.pptx", "Performance-Audit-Discussion.pdf"],
        filter_by="filename",
        export_filename="filtered_metrics.tsv",
        export_dir=export_dir,
        return_type="file",
    )
    filtered_df = pd.read_csv(os.path.join(export_dir, "filtered_metrics.tsv"), sep="\t")

    get_mean_grouping(
        group_by="all",
        data_input=filtered_df,
        export_dir=export_dir,
        eval_name="text_extraction",
        export_filename="two-filename-agg-cct.tsv",
    )
    grouped_df = pd.read_csv(os.path.join(export_dir, "two-filename-agg-cct.tsv"), sep="\t")

    assert np.isclose(float(grouped_df.iloc[1, 0]), 0.903)
    assert np.isclose(float(grouped_df.iloc[1, 1]), 0.129)
    assert np.isclose(float(grouped_df.iloc[1, 2]), 0.091)


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_get_mean_grouping_all_file_txt():
    with open(os.path.join(TESTING_FILE_DIR, "filter_list.txt"), "w") as file:
        file.write("Bank Good Credit Loan.pptx\n")
        file.write("Performance-Audit-Discussion.pdf\n")
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")

    filter_metrics(
        data_input=DUMMY_DF_CCT,
        filter_list=os.path.join(TESTING_FILE_DIR, "filter_list.txt"),
        filter_by="filename",
        export_filename="filtered_metrics.tsv",
        export_dir=export_dir,
        return_type="file",
    )
    filtered_df = pd.read_csv(os.path.join(export_dir, "filtered_metrics.tsv"), sep="\t")

    get_mean_grouping(
        group_by="all",
        data_input=filtered_df,
        export_dir=export_dir,
        eval_name="text_extraction",
        export_filename="two-filename-agg-cct.tsv",
    )
    grouped_df = pd.read_csv(os.path.join(export_dir, "two-filename-agg-cct.tsv"), sep="\t")

    assert np.isclose(float(grouped_df.iloc[1, 0]), 0.903)
    assert np.isclose(float(grouped_df.iloc[1, 1]), 0.129)
    assert np.isclose(float(grouped_df.iloc[1, 2]), 0.091)
