"""Preserve structural cells through HTML v2 conversion and public chunking."""

from __future__ import annotations

import copy

import pytest
from lxml.html import fragment_fromstring

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Table
from unstructured.partition.html.transformations import (
    ontology_to_unstructured_elements,
    parse_html_to_ontology,
)


@pytest.mark.parametrize("chunker", [chunk_elements, chunk_by_title])
@pytest.mark.parametrize("cell_tag", ["td", "th"])
@pytest.mark.parametrize("single_row", [False, True])
def test_v2_semantic_cells_survive_table_splits(chunker, cell_tag: str, single_row: bool):
    cells = [
        f'<{cell_tag} class="Currency">${100 + i}</{cell_tag}><td>visible-value-{i}</td>'
        for i in range(8)
    ]
    rows = ["".join(cells)] if single_row else cells
    html = (
        '<body class="Document"><table>'
        + "".join(f"<tr>{row}</tr>" for row in rows)
        + "</table></body>"
    )
    expected = [text for i in range(8) for text in (f"${100 + i}", f"visible-value-{i}")]
    (table,) = ontology_to_unstructured_elements(parse_html_to_ontology(html))
    assert isinstance(table, Table)
    source = copy.deepcopy(table.to_dict())

    chunks = chunker([table], max_characters=50)

    assert len(chunks) > 1
    assert " ".join(chunk.text for chunk in chunks).split() == expected
    assert [
        "".join(cell.itertext())
        for chunk in chunks
        for cell in fragment_fromstring(chunk.metadata.text_as_html).xpath("./tr/td | ./tr/th")
    ] == expected
    assert table.to_dict() == source
    assert all(chunk.metadata.orig_elements[0].to_dict() == source for chunk in chunks)


@pytest.mark.parametrize(
    ("tag", "class_name", "expected_tag"),
    [
        ("td", "Currency", "td"),
        ("th", "Currency", "th"),
        ("span", "Currency", "span"),
        ("p", "Currency", "span"),
        ("p", "Sidebar", "aside"),
    ],
)
def test_cell_structure_takes_priority_without_changing_other_typed_tags(
    tag: str, class_name: str, expected_tag: str
):
    html = f'<body class="Document"><{tag} class="{class_name}">$100</{tag}></body>'

    document = parse_html_to_ontology(html)
    (element,) = document.children

    assert element.__class__.__name__ == class_name
    assert element.html_tag_name == expected_tag
    assert element.to_text() == "$100"
