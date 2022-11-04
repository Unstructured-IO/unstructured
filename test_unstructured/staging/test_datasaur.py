import pytest

import unstructured.staging.datasaur as datasaur

from unstructured.documents.elements import Text


def test_stage_for_datasaur():
    elements = [Text("Text 1"),Text("Text 2"),Text("Text 3")]
    result = datasaur.stage_for_datasaur(elements)
    assert result[0]["text"] == "Text 1"
    assert result[0]["entities"] == []
    assert result[1]["text"] == "Text 2"
    assert result[1]["entities"] == []    
    assert result[2]["text"] == "Text 3"
    assert result[2]["entities"] == []