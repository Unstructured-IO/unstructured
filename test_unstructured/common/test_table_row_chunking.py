"""Exercise HTML row traversal through public table chunking."""

from __future__ import annotations

import pytest
from lxml.html import fragment_fromstring

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
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
