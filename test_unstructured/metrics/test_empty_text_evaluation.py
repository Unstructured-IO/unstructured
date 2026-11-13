import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pytest

from unstructured.metrics.evaluate import TextExtractionMetricsCalculator


@pytest.mark.parametrize("document_type", ["txt", "json"])
@pytest.mark.parametrize(
    ("prediction", "source", "accuracy", "missing"),
    [
        ("", "", 1.0, 0.0),
        ("unexpected text", "", 0.0, 0.0),
        ("", "reference text", 0.0, 1.0),
        ("", " \n\t", 1.0, 0.0),
        ("same text", "same text", 1.0, 0.0),
        ("short", "much longer reference text" * 10, 0.01, 1.0),
    ],
)
def test_text_evaluation_keeps_empty_documents_and_their_scores(
    tmp_path, document_type, prediction, source, accuracy, missing
):
    documents = tmp_path / "documents"
    references = tmp_path / "references"
    reports = tmp_path / "reports"
    documents.mkdir()
    references.mkdir()
    if document_type == "json":
        elements = (
            [{"type": "NarrativeText", "text": prediction, "metadata": {}}] if prediction else []
        )
        content = json.dumps(elements)
    else:
        content = prediction
    (documents / f"sample.pdf.{document_type}").write_text(content, encoding="utf-8")
    (references / "sample.pdf.txt").write_text(source, encoding="utf-8")
    calculator = TextExtractionMetricsCalculator(documents, references, document_type=document_type)

    with ThreadPoolExecutor(max_workers=1) as executor:
        result = calculator.calculate(
            executor=executor,
            export_dir=reports,
            visualize_progress=False,
            display_agg_df=False,
        )

    assert len(result) == 1
    assert result.iloc[0]["filename"] == "sample.pdf"
    assert result.iloc[0]["cct-accuracy"] == accuracy
    assert result.iloc[0]["cct-%missing"] == missing
    aggregate = pd.read_csv(reports / "aggregate-scores-cct.tsv", sep="\t").set_index("metric")
    assert aggregate.loc["cct-accuracy", "count"] == 1
    assert aggregate.loc["cct-accuracy", "average"] == accuracy
