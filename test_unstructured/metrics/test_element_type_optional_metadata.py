import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pytest

from unstructured.metrics.element_type import get_element_type_frequency
from unstructured.metrics.evaluate import ElementTypeMetricsCalculator
from unstructured.staging.base import elements_from_dicts, elements_to_json


def _elements(metadata_mode):
    title = {"type": "Title", "text": "A heading"}
    if metadata_mode != "missing":
        title["metadata"] = None if metadata_mode == "null" else {}
    return [
        title,
        {"type": "NarrativeText", "text": "A paragraph", "metadata": {"category_depth": 0}},
    ]


@pytest.mark.parametrize("metadata_mode", ["missing", "null", "empty"])
def test_element_frequency_accepts_the_same_optional_metadata_as_json_staging(metadata_mode):
    elements = _elements(metadata_mode)
    expected = {("Title", None): 1, ("NarrativeText", 0): 1}

    # Staging already accepts these serialized elements and normalizes optional metadata.
    assert get_element_type_frequency(elements_to_json(elements_from_dicts(elements))) == expected
    assert get_element_type_frequency(json.dumps(elements)) == expected


@pytest.mark.parametrize("metadata_mode", ["missing", "null", "empty"])
@pytest.mark.parametrize("side", ["prediction", "reference"])
def test_optional_metadata_does_not_silently_remove_a_document_from_metrics(
    tmp_path, metadata_mode, side
):
    documents = tmp_path / "documents"
    references = tmp_path / "references"
    reports = tmp_path / "reports"
    documents.mkdir()
    references.mkdir()
    for name, directory in [("prediction", documents), ("reference", references)]:
        elements = _elements(metadata_mode if name == side else "empty")
        (directory / "document.pdf.json").write_text(json.dumps(elements), encoding="utf-8")

    calculator = ElementTypeMetricsCalculator(documents, references)
    with ThreadPoolExecutor(max_workers=1) as executor:
        rows = calculator.calculate(
            executor=executor,
            export_dir=reports,
            visualize_progress=False,
            display_agg_df=False,
        )

    assert len(rows) == 1
    assert rows.iloc[0]["element-type-accuracy"] == 1
    aggregate = pd.read_csv(reports / calculator.default_agg_tsv_name, sep="\t")
    assert aggregate.iloc[0]["count"] == 1
    assert aggregate.iloc[0]["average"] == 1


@pytest.mark.parametrize("depth", [0, 2])
def test_optional_metadata_normalization_preserves_explicit_category_depth(depth):
    elements = [
        {"type": "Title", "text": "Default", "metadata": {}},
        {"type": "Title", "text": "Explicit", "metadata": {"category_depth": depth}},
    ]

    assert get_element_type_frequency(json.dumps(elements)) == {
        ("Title", None): 1,
        ("Title", depth): 1,
    }
