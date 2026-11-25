import csv
import io

import pytest
from lxml import etree

from unstructured.partition.csv import _record_is_complete, partition_csv
from unstructured.partition.tsv import partition_tsv


@pytest.mark.parametrize(
    ("partitioner", "separator", "extension"),
    [(partition_csv, ",", "csv"), (partition_csv, ";", "csv"), (partition_tsv, "\t", "tsv")],
)
@pytest.mark.parametrize(
    "labels",
    [["name", "name"], ["name", "name.1", "name"], ['say"hi', 'say"hi']],
)
@pytest.mark.parametrize("from_file", [False, True])
def test_quoted_duplicate_headers_survive_eof_without_a_newline(
    partitioner, separator, extension, labels, from_file, tmp_path
):
    content = io.StringIO()
    csv.writer(content, delimiter=separator, quoting=csv.QUOTE_ALL, lineterminator="").writerow(
        labels
    )
    data = content.getvalue().encode()
    if from_file:
        path = tmp_path / f"headers.{extension}"
        path.write_bytes(data)
        source = {"filename": str(path)}
    else:
        source = {"file": io.BytesIO(data)}

    elements = partitioner(**source, include_header=True, languages=[""])

    assert len(elements) == 1
    assert elements[0].text == " ".join(labels)
    table = etree.fromstring(elements[0].metadata.text_as_html)
    assert ["".join(cell.itertext()) for cell in table.iter("td")] == labels


@pytest.mark.parametrize(
    ("partitioner", "separator"),
    [(partition_csv, ","), (partition_csv, ";"), (partition_tsv, "\t")],
)
@pytest.mark.parametrize("terminator", ["\n", "\r\n"])
def test_terminated_quoted_headers_keep_the_same_output(partitioner, separator, terminator):
    data = f'"name"{separator}"name"{terminator}'.encode()

    elements = partitioner(file=io.BytesIO(data), include_header=True, languages=[""])

    assert len(elements) == 1
    assert elements[0].text == "name name"


@pytest.mark.parametrize("record", ['"name', '"name""', '"name\n'])
def test_an_unclosed_quoted_field_is_still_incomplete(record):
    assert not _record_is_complete(record, ",")
