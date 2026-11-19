import re

import pytest

from unstructured.cleaners import extract


@pytest.mark.parametrize("extractor", [extract.extract_text_before, extract.extract_text_after])
@pytest.mark.parametrize("index", [0, 1, 3])
def test_text_extraction_does_not_scan_beyond_the_requested_match(monkeypatch, extractor, index):
    text = "zero | one | two | three | four | five"
    finditer = re.finditer
    matches = list(finditer(r"\|", text))
    visited = []

    def counting_finditer(pattern, value):
        for match in finditer(pattern, value):
            visited.append(match.span())
            yield match

    monkeypatch.setattr(extract.re, "finditer", counting_finditer)

    result = extractor(text, r"\|", index=index, strip=False)

    match = matches[index]
    expected = (
        text[: match.start()] if extractor is extract.extract_text_before else text[match.end() :]
    )
    assert result == expected
    assert visited == [match.span() for match in matches[: index + 1]]


def test_text_extraction_still_reports_the_last_available_index():
    with pytest.raises(ValueError, match="largest index was 1"):
        extract.extract_text_before("one | two | three", r"\|", index=2)
