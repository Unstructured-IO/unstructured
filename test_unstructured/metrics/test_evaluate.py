import os
import pathlib
import shutil

import pandas as pd
import pytest

from unstructured.metrics.evaluate import (
    get_mean_grouping,
    measure_element_type_accuracy,
    measure_table_structure_accuracy,
    measure_text_extraction_accuracy,
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
    # Run test as normal
    yield

    def remove_generated_directories():
        """Remove directories created from running tests"""
        # Directories to be removed:
        target_dir_names = ["test_evaluate_results_cct", "test_evaluate_results_cct_txt"]
        subdirs = (d for d in os.scandir(TESTING_FILE_DIR) if d.is_dir())
        for d in subdirs:
            if d.name in target_dir_names:
                shutil.rmtree(d.path)

    remove_generated_directories()


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_text_extraction_evaluation():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")
    measure_text_extraction_accuracy(
        output_dir=output_dir, source_dir=source_dir, export_dir=export_dir
    )
    assert os.path.isfile(os.path.join(export_dir, "all-docs-cct.tsv"))
    df = pd.read_csv(os.path.join(export_dir, "all-docs-cct.tsv"), sep="\t")
    assert len(df) == 3
    assert len(df.columns) == 5
    assert df.iloc[0].filename == "Bank Good Credit Loan.pptx"


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_text_extraction_evaluation_type_txt():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_CCT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")
    measure_text_extraction_accuracy(
        output_dir=output_dir, source_dir=source_dir, export_dir=export_dir, output_type="txt"
    )
    assert os.path.isfile(os.path.join(export_dir, "all-docs-cct.tsv"))
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
    measure_element_type_accuracy(
        output_dir=output_dir, source_dir=source_dir, export_dir=export_dir
    )
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
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_table_structure")
    measure_table_structure_accuracy(
        output_dir=output_dir, source_dir=source_dir, export_dir=export_dir
    )
    assert os.path.isfile(os.path.join(export_dir, "all-docs-table-structure-accuracy.tsv"))
    assert os.path.isfile(os.path.join(export_dir, "aggregate-table-structure-accuracy.tsv"))
    df = pd.read_csv(os.path.join(export_dir, "all-docs-table-structure-accuracy.tsv"), sep="\t")
    assert len(df) == 1
    assert len(df.columns) == 9
    assert df.iloc[0].filename == "IRS-2023-Form-1095-A.pdf"


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_text_extraction_takes_list():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    output_list = ["currency.csv.json"]
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")
    measure_text_extraction_accuracy(
        output_dir=output_dir,
        source_dir=source_dir,
        output_list=output_list,
        export_dir=export_dir,
    )
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
    measure_text_extraction_accuracy(
        output_dir=output_dir, source_dir=source_dir, export_dir=export_dir, grouping="doctype"
    )
    df = pd.read_csv(os.path.join(export_dir, "all-doctype-agg-cct.tsv"), sep="\t")
    assert len(df) == 4  # metrics row and doctype rows


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_text_extraction_wrong_type():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")
    with pytest.raises(ValueError):
        measure_text_extraction_accuracy(
            output_dir=output_dir, source_dir=source_dir, export_dir=export_dir, output_type="wrong"
        )


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
@pytest.mark.parametrize(("grouping", "count_row"), [("doctype", 3), ("connector", 2)])
def test_get_mean_grouping_df_input(grouping, count_row):
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")
    get_mean_grouping(
        grouping=grouping,
        data_input=DUMMY_DF_CCT,
        export_dir=export_dir,
        metric_strategy="text_extraction",
    )
    grouped_df = pd.read_csv(os.path.join(export_dir, f"all-{grouping}-agg-cct.tsv"), sep="\t")
    assert grouped_df[grouping].dropna().nunique() == count_row


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_get_mean_grouping_tsv_input():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")
    measure_text_extraction_accuracy(
        output_dir=output_dir, source_dir=source_dir, export_dir=export_dir
    )
    filename = os.path.join(export_dir, "all-docs-cct.tsv")
    get_mean_grouping(
        grouping="doctype",
        data_input=filename,
        export_dir=export_dir,
        metric_strategy="text_extraction",
    )
    grouped_df = pd.read_csv(os.path.join(export_dir, "all-doctype-agg-cct.tsv"), sep="\t")
    assert grouped_df["doctype"].dropna().nunique() == 3


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
def test_get_mean_grouping_invalid_group():
    output_dir = os.path.join(TESTING_FILE_DIR, UNSTRUCTURED_OUTPUT_DIRNAME)
    source_dir = os.path.join(TESTING_FILE_DIR, GOLD_CCT_DIRNAME)
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_cct")
    measure_text_extraction_accuracy(
        output_dir=output_dir, source_dir=source_dir, export_dir=export_dir
    )
    df = pd.read_csv(os.path.join(export_dir, "all-docs-cct.tsv"), sep="\t")
    with pytest.raises(ValueError):
        get_mean_grouping(
            grouping="invalid",
            data_input=df,
            export_dir=export_dir,
            metric_strategy="text_extraction",
        )


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_text_extraction_grouping_empty_df():
    empty_df = pd.DataFrame()
    with pytest.raises(SystemExit):
        get_mean_grouping("doctype", empty_df, "some_dir", metric_strategy="text_extraction")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_get_mean_grouping_missing_grouping_column():
    df_with_no_grouping = pd.DataFrame({"some_column": [1, 2, 3]})
    with pytest.raises(SystemExit):
        get_mean_grouping("doctype", df_with_no_grouping, "some_dir", "text-extraction")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_get_mean_grouping_all_null_grouping_column():
    df_with_null_grouping = pd.DataFrame({"doctype": [None, None, None]})
    with pytest.raises(SystemExit):
        get_mean_grouping(
            "doctype", df_with_null_grouping, "some_dir", metric_strategy="text_extraction"
        )


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_get_mean_grouping_invalid_metric_strategy():
    with pytest.raises(ValueError):
        get_mean_grouping("doctype", DUMMY_DF_ELEMENT_TYPE, "some_dir", metric_strategy="invalid")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test")
@pytest.mark.parametrize(("grouping", "count_row"), [("doctype", 3), ("connector", 2)])
def test_get_mean_grouping_element_type(grouping, count_row):
    export_dir = os.path.join(TESTING_FILE_DIR, "test_evaluate_results_element_type")
    get_mean_grouping(
        grouping=grouping,
        data_input=DUMMY_DF_ELEMENT_TYPE,
        export_dir=export_dir,
        metric_strategy="element_type",
    )
    grouped_df = pd.read_csv(
        os.path.join(export_dir, f"all-{grouping}-agg-element-type.tsv"), sep="\t"
    )
    assert grouped_df[grouping].dropna().nunique() == count_row
