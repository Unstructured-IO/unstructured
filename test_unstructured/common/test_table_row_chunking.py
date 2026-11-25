"""Exercise HTML row traversal through public table chunking."""

from __future__ import annotations

import copy

import pytest
from lxml.html import fragment_fromstring

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.common.html_table import HtmlTable
from unstructured.documents.elements import ElementMetadata, Table


@pytest.mark.parametrize("chunker", [chunk_elements, chunk_by_title])
@pytest.mark.parametrize("max_characters", [50, 80])
@pytest.mark.parametrize(
    "non_cell",
    [
        "<!-- layout marker -->",
        "<?layout marker?>",
        "<template>hidden</template>",
        "<script>hidden</script>",
    ],
)
def test_table_chunks_skip_non_cell_children(chunker, max_characters: int, non_cell: str):
    html = (
        "<table>"
        + "".join(
            f"<tr>{non_cell}<td>row{i}</td>{non_cell}<td>value{i}</td>{non_cell}</tr>"
            for i in range(3)
        )
        + "</table>"
    )
    expected = [text for i in range(3) for text in (f"row{i}", f"value{i}")]
    table = Table(" ".join(expected), metadata=ElementMetadata(text_as_html=html))

    chunks = chunker([table], max_characters=max_characters)

    assert " ".join(chunk.text for chunk in chunks).split() == expected
    assert all(chunk.metadata.text_as_html for chunk in chunks)
    assert [
        "".join(cell.itertext())
        for chunk in chunks
        for cell in fragment_fromstring(chunk.metadata.text_as_html).xpath("./tr/td | ./tr/th")
    ] == expected
    assert table.metadata.text_as_html == html
    assert table.text.split() == expected


@pytest.mark.parametrize("chunker", [chunk_elements, chunk_by_title])
@pytest.mark.parametrize(
    "non_cell",
    [
        "<template>{payload}</template>",
        "<script>{payload}</script>",
        "<!-- {payload} -->",
        "<?layout {payload}?>",
    ],
)
def test_ignored_row_payload_does_not_leak_into_chunk_html(chunker, non_cell: str):
    payload = "HIDDEN" * 2_000
    html = f"<table><tr><td>A</td>{non_cell.format(payload=payload)}</tr></table>"
    table = Table("A", metadata=ElementMetadata(text_as_html=html))
    source = copy.deepcopy(table.to_dict())

    chunks = chunker([table], max_characters=500)

    assert [chunk.text for chunk in chunks] == ["A"]
    assert chunks[0].metadata.text_as_html == "<table><tr><td>A</td></tr></table>"
    assert table.to_dict() == source
    assert chunks[0].metadata.orig_elements[0].to_dict() == source


def test_working_rows_keep_cell_markup_and_original_non_cell_source():
    html = (
        '<table><thead><tr data-row="original"><!-- layout -->'
        "<template>hidden</template><th><b>Header</b></th>"
        '<th colspan="2">Value</th></tr></thead></table>'
    )

    table = HtmlTable.from_html_text(html)
    (row,) = table.iter_rows()

    assert row.is_header
    assert row.html == '<tr><td><b>Header</b></td><td colspan="2">Value</td></tr>'
    assert list(row.iter_cell_texts()) == ["Header", "Value"]
    original = fragment_fromstring(row.source_html)
    assert original.get("data-row") == "original"
    assert original.xpath("./template/text()") == ["hidden"]
    assert len(original.xpath("./comment()")) == 1
    assert original.xpath("./th/@colspan") == ["2"]


@pytest.mark.parametrize("chunker", [chunk_elements, chunk_by_title])
@pytest.mark.parametrize(
    "non_cell",
    [
        "<template>{payload}</template>",
        "<script>{payload}</script>",
        "<!-- {payload} -->",
        "<?layout {payload}?>",
    ],
)
def test_repeated_headers_do_not_restore_ignored_source_nodes(chunker, non_cell: str):
    payload = "HIDDEN" * 10
    rows = [f"row{i} alpha beta gamma delta epsilon" for i in range(8)]
    html = (
        '<table><thead><tr data-row="original">'
        '<th scope="col" class="measure" data-label="primary"><b>Header Amount</b></th>'
        + non_cell.format(payload=payload)
        + "</tr></thead><tbody>"
        + "".join(f"<tr><td>{row}</td></tr>" for row in rows)
        + "</tbody></table>"
    )
    table = Table("Header Amount " + " ".join(rows), metadata=ElementMetadata(text_as_html=html))
    source = copy.deepcopy(table.to_dict())
    source_header = next(HtmlTable.from_html_text(html).iter_rows()).source_html
    assert payload in source_header

    chunks = chunker([table], max_characters=100)

    assert len(chunks) > 1
    assert table.to_dict() == source
    assert all(chunk.metadata.orig_elements[0].to_dict() == source for chunk in chunks)
    for chunk in chunks[1:]:
        assert chunk.text.startswith("Header Amount ")
        root = fragment_fromstring(chunk.metadata.text_as_html)
        (header,) = root.xpath("./thead/tr/th")
        assert header.get("scope") == "col"
        assert header.get("class") == "measure"
        assert header.get("data-label") == "primary"
        assert header.xpath("./b/text()") == ["Header Amount"]
        assert header.getparent().get("data-row") == "original"
        assert payload not in chunk.metadata.text_as_html
        assert not root.xpath(
            ".//template | .//script | .//comment() | .//processing-instruction()"
        )
    assert all(payload not in chunk.metadata.text_as_html for chunk in chunks)
