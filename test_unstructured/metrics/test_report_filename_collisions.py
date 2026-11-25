import pandas as pd
import pytest

from unstructured.metrics.utils import _uniquity_file, _write_to_file


@pytest.mark.parametrize(
    ("target", "existing", "expected"),
    [
        (
            "report (2026).tsv",
            ["report (2026).tsv", "report (2026) (1).tsv"],
            "report (2026) (2).tsv",
        ),
        (
            "report.tsv",
            ["report.tsv", "report (01).tsv", "report (1).tsv", "report (2).tsv"],
            "report (3).tsv",
        ),
        (
            "report (1).tsv",
            ["report (1).tsv", "report (1) (2).tsv", "report (1) (3).tsv"],
            "report (1) (1).tsv",
        ),
        ("report.tsv", ["report.tsv", "report (1).tsv", "report (3).tsv"], "report (2).tsv"),
        ("report.tsv", ["other (1).tsv", "report (1).csv"], "report (1).tsv"),
    ],
)
def test_report_collision_suffixes_are_distinct_from_numbers_in_the_base_name(
    target, existing, expected
):
    result = _uniquity_file(existing, target)

    assert result == expected
    assert result not in existing


@pytest.mark.parametrize(
    ("target", "existing"),
    [
        ("report (2026).tsv", ["report (2026).tsv", "report (2026) (1).tsv"]),
        ("report.tsv", ["report.tsv", "report (01).tsv", "report (1).tsv", "report (2).tsv"]),
    ],
)
def test_no_overwrite_report_export_keeps_every_existing_file(tmp_path, target, existing):
    original = {name: f"existing content for {name}\n" for name in existing}
    for name, contents in original.items():
        (tmp_path / name).write_text(contents, encoding="utf-8")

    _write_to_file(str(tmp_path), target, pd.DataFrame({"score": [0.9]}), overwrite=False)

    assert {name: (tmp_path / name).read_text(encoding="utf-8") for name in original} == original
    created = {path.name for path in tmp_path.iterdir()} - set(existing)
    assert len(created) == 1
    report = pd.read_csv(tmp_path / created.pop(), sep="\t")
    assert report["score"].tolist() == [0.9]
