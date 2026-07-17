import json

import pytest

from scripts.performance import benchmark_text_partition as benchmark
from unstructured.documents.elements import Text, Title


def test_fingerprint_captures_element_types_and_text():
    digest, type_counts = benchmark.fingerprint([Title("Heading"), Text("Body")])

    assert digest == "e9093cf43e539c4b37dbf00776d267318e9041c8de09e216e82e1c17a099f073"
    assert type_counts == {"Text": 1, "Title": 1}


def test_run_benchmark_measures_each_document_without_nlp_result_cache_hits(monkeypatch, tmp_path):
    warmup = tmp_path / "warmup.txt"
    inputs = [tmp_path / "document.html", tmp_path / "document.docx"]
    partitioned_paths = []
    cache_clears = []

    def fake_partition(*, filename, strategy):
        assert strategy == "fast"
        partitioned_paths.append(filename)
        return [Text(text=filename)]

    monkeypatch.setattr(benchmark, "partition", fake_partition)
    monkeypatch.setattr(benchmark, "clear_nlp_result_caches", lambda: cache_clears.append(True))

    results = benchmark.run_benchmark(inputs, warmup, iterations=2)

    assert partitioned_paths == [
        str(warmup),
        str(inputs[0]),
        str(inputs[0]),
        str(inputs[1]),
        str(inputs[1]),
    ]
    assert len(cache_clears) == 5
    assert list(results["documents"]) == [str(path) for path in inputs]
    assert results["documents"][str(inputs[0])]["output"]["element_count"] == 1


def test_compare_results_checks_each_document_output(tmp_path, capsys):
    output = {"sha256": "same", "element_count": 1, "type_counts": {"Text": 1}}
    baseline = {
        "documents": {"document.txt": {"seconds": {"median": 2.0}, "output": output}},
        "summary": {"median_total_seconds": 2.0},
    }
    current = {
        "documents": {"document.txt": {"seconds": {"median": 1.0}, "output": output}},
        "summary": {"median_total_seconds": 1.0},
    }
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline))

    benchmark.compare_results(current, baseline_path)

    stdout = capsys.readouterr().out
    assert "exact output; 2.000s -> 1.000s" in stdout
    assert "Aggregate speedup: 2.00x (50.0% faster)" in stdout


def test_compare_results_rejects_output_regression(tmp_path):
    baseline = {
        "documents": {
            "document.txt": {
                "seconds": {"median": 2.0},
                "output": {"sha256": "baseline"},
            }
        },
        "summary": {"median_total_seconds": 2.0},
    }
    current = {
        "documents": {
            "document.txt": {
                "seconds": {"median": 1.0},
                "output": {"sha256": "changed"},
            }
        },
        "summary": {"median_total_seconds": 1.0},
    }
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline))

    with pytest.raises(SystemExit, match="candidate output differs for document.txt"):
        benchmark.compare_results(current, baseline_path)
