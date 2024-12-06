import os
import pathlib
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

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


@pytest.fixture
def mock_dependencies():
    with patch(
        "unstructured.metrics.evaluate.calculate_accuracy"
    ) as mock_calculate_accuracy, patch(
        "unstructured.metrics.evaluate.calculate_percent_missing_text"
    ) as mock_calculate_percent_missing_text, patch.object(
        TextExtractionMetricsCalculator, "_get_ccts"
    ) as mock_get_ccts, patch(
        "unstructured.metrics.evaluate.get_element_type_frequency"
    ) as mock_get_element_type_frequency, patch(
        "unstructured.metrics.evaluate.calculate_element_type_percent_match"
    ) as mock_calculate_element_type_percent_match, patch(
        "unstructured.metrics.evaluate._read_text_file"
    ) as mock_read_text_file, patch.object(
        Path, "exists"
    ) as mock_path_exists, patch(
        "unstructured.metrics.evaluate.TableEvalProcessor.from_json_files"
    ) as mock_table_eval_processor_from_json_files, patch.object(
        TableStructureMetricsCalculator, "supported_metric_names"
    ) as mock_supported_metric_names:
        mocks = {
            "mock_calculate_accuracy": mock_calculate_accuracy,
            "mock_calculate_percent_missing_text": mock_calculate_percent_missing_text,
            "mock_get_ccts": mock_get_ccts,
            "mock_get_element_type_frequency": mock_get_element_type_frequency,
            "mock_read_text_file": mock_read_text_file,
            "mock_calculate_element_type_percent_match": mock_calculate_element_type_percent_match,
            "mock_table_eval_processor_from_json_files": mock_table_eval_processor_from_json_files,
            "mock_supported_metric_names": mock_supported_metric_names,
            "mock_path_exists": mock_path_exists,
        }

        # setup mocks
        mocks["mock_calculate_accuracy"].return_value = 0.5
        mocks["mock_calculate_percent_missing_text"].return_value = 0.5
        mocks["mock_get_ccts"].return_value = ["output_cct", "source_cct"]
        mocks["mock_get_element_type_frequency"].side_effect = [{"ele1": 1}, {"ele2": 3}]
        mocks["mock_calculate_element_type_percent_match"].return_value = 0.5
        mocks["mock_supported_metric_names"].return_value = ["table_level_acc"]
        mocks["mock_path_exists"].return_value = True
        mocks["mock_read_text_file"].side_effect = ["output_text", "source_text"]

        yield mocks


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
            14,
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
@pytest.mark.usefixtures("_cleanup_after_test", "mock_dependencies")
@pytest.mark.parametrize(
    ("calculator_class", "output_dirname", "source_dirname", "path", "kwargs"),
    [
        (
            TextExtractionMetricsCalculator,
            UNSTRUCTURED_CCT_DIRNAME,
            GOLD_CCT_DIRNAME,
            Path("2310.03502text_to_image_synthesis1-7.pdf.txt"),
            {"document_type": "txt"},
        ),
    ],
)
def test_TextExtractionMetricsCalculator_process_document_returns_the_correct_doctype(
    mock_dependencies, calculator_class, output_dirname, source_dirname, path, kwargs
):

    output_dir = Path(TESTING_FILE_DIR) / output_dirname
    source_dir = Path(TESTING_FILE_DIR) / source_dirname
    mock_calculate_accuracy = mock_dependencies["mock_calculate_accuracy"]
    mock_calculate_percent_missing_text = mock_dependencies["mock_calculate_percent_missing_text"]
    mock_get_ccts = mock_dependencies["mock_get_ccts"]
    calculator = calculator_class(documents_dir=output_dir, ground_truths_dir=source_dir, **kwargs)
    output_list = calculator._process_document(path)
    assert output_list[1] == ".pdf"
    assert mock_calculate_accuracy.call_count == 1
    assert mock_calculate_percent_missing_text.call_count == 1
    assert mock_get_ccts.call_count == 1


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test", "mock_dependencies")
@pytest.mark.parametrize(
    ("calculator_class", "output_dirname", "source_dirname", "path", "kwargs"),
    [
        (
            TableStructureMetricsCalculator,
            UNSTRUCTURED_TABLE_STRUCTURE_DIRNAME,
            GOLD_TABLE_STRUCTURE_DIRNAME,
            Path("tablib-627mTABLES-2310.07875-p7.pdf.json"),
            {},
        ),
        # (
        #     ElementTypeMetricsCalculator,
        #     UNSTRUCTURED_OUTPUT_DIRNAME,
        #     GOLD_ELEMENT_TYPE_DIRNAME,
        #     Path("IRS-form.1987.pdf.json"),
        #     {},
        # ),
    ],
)
def test_TableStructureMetricsCalculator_process_document_returns_the_correct_doctype(
    mock_dependencies, calculator_class, output_dirname, source_dirname, path, kwargs
):

    output_dir = Path(TESTING_FILE_DIR) / output_dirname
    source_dir = Path(TESTING_FILE_DIR) / source_dirname
    calculator = calculator_class(documents_dir=output_dir, ground_truths_dir=source_dir, **kwargs)
    calculator._ground_truths_dir = source_dir
    calculator._documents_dir = output_dir
    calculator._ground_truth_paths = [source_dir / path]
    mock_report = MagicMock()
    mock_report.total_predicted_tables = 3
    mock_report.table_evel_acc = 0.83
    mock_table_eval_processor_from_json_files = mock_dependencies[
        "mock_table_eval_processor_from_json_files"
    ]
    mock_table_eval_processor_from_json_files.return_value.process_file.return_value = mock_report

    output_list = calculator._process_document(path)
    assert output_list[1] == ".pdf"
    assert mock_table_eval_processor_from_json_files.call_count == 1


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.usefixtures("_cleanup_after_test", "mock_dependencies")
@pytest.mark.parametrize(
    ("calculator_class", "output_dirname", "source_dirname", "path", "kwargs"),
    [
        (
            ElementTypeMetricsCalculator,
            UNSTRUCTURED_OUTPUT_DIRNAME,
            GOLD_ELEMENT_TYPE_DIRNAME,
            Path("IRS-form.1987.pdf.json"),
            {},
        ),
    ],
)
def test_ElementTypeMetricsCalculator_process_document_returns_the_correct_doctype(
    mock_dependencies, calculator_class, output_dirname, source_dirname, path, kwargs
):

    output_dir = Path(TESTING_FILE_DIR) / output_dirname
    source_dir = Path(TESTING_FILE_DIR) / source_dirname
    calculator = calculator_class(documents_dir=output_dir, ground_truths_dir=source_dir, **kwargs)
    mock_element_type_frequency = mock_dependencies["mock_get_element_type_frequency"]
    mock_read_text_file = mock_dependencies["mock_read_text_file"]
    mock_calculate_element_type_percent_match = mock_dependencies[
        "mock_calculate_element_type_percent_match"
    ]
    output_list = calculator._process_document(path)
    assert output_list[1] == ".pdf"
    assert mock_read_text_file.call_count == 2
    assert mock_element_type_frequency.call_count == 2
    assert mock_calculate_element_type_percent_match.call_count == 1


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
    agg_df = pd.read_csv(
        os.path.join(export_dir, "aggregate-table-structure-accuracy.tsv"), sep="\t"
    ).set_index("metric")
    assert len(df) == 2
    assert len(df.columns) == 15
    assert df.iloc[1].filename == "IRS-2023-Form-1095-A.pdf"
    assert (
        np.round(np.average(df["table_level_acc"], weights=df["total_tables"]), 3)
        == agg_df.loc["table_level_acc", "average"]
    )


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
