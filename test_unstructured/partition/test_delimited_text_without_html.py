import csv
from io import BytesIO, StringIO

import pytest

from unstructured.partition.csv import partition_csv
from unstructured.partition.tsv import partition_tsv


@pytest.mark.parametrize(
    ("partitioner", "delimiter"), [(partition_csv, ","), (partition_tsv, "\t")]
)
@pytest.mark.parametrize("include_header", [False, True])
@pytest.mark.parametrize(
    "rows",
    [
        [["name", "amount"], ["Ada", "001"], ["Bo", "N/A"]],
        [["", "name", "name", "name.1"], ["", "A", "B", "C"]],
        [["head\nline", "head\twith\ttab"], ["a\nb", " c\t d "]],
        [["name", "value"], ["<b>literal</b>", "&nbsp; & < > \" '"], ["東京", "emoji 🛰️"]],
        [["a", "b", "c"], ["a", "b"], ["", "", ""]],
        [["name", "value"], ["alpha", "a\x00b"], ["beta", "\x0b\x0cvalue"]],
        [["head", "only"]],
        [],
    ],
)
def test_disabling_html_preserves_text_and_all_other_serialized_fields(
    partitioner, delimiter, include_header, rows
):
    with StringIO(newline="") as buffer:
        csv.writer(buffer, delimiter=delimiter).writerows(rows)
        payload = buffer.getvalue().encode("utf-8")
    kwargs = {"include_header": include_header, "languages": ["eng"]}

    with_html = partitioner(file=BytesIO(payload), infer_table_structure=True, **kwargs)
    without_html = partitioner(file=BytesIO(payload), infer_table_structure=False, **kwargs)

    expected = [element.to_dict() for element in with_html]
    for element in expected:
        element["metadata"].pop("text_as_html", None)
    assert [element.to_dict() for element in without_html] == expected
    assert all(element.metadata.text_as_html is None for element in without_html)


@pytest.mark.parametrize(
    ("partitioner", "delimiter"), [(partition_csv, ","), (partition_tsv, "\t")]
)
@pytest.mark.parametrize("include_header", [False, True])
def test_incompatible_xml_characters_retain_the_existing_error(
    partitioner, delimiter, include_header
):
    payload = f"name{delimiter}value\nfirst{delimiter}a\x01b\n".encode()
    for infer_table_structure in (True, False):
        with pytest.raises(ValueError, match="XML compatible"):
            partitioner(
                file=BytesIO(payload),
                include_header=include_header,
                infer_table_structure=infer_table_structure,
                languages=["eng"],
            )
