"""An empty language selection uses the existing automatic detection mode."""

import pytest

from unstructured.documents.elements import ElementMetadata, NarrativeText
from unstructured.partition.common.lang import apply_lang_metadata, detect_languages


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("This is a longer English sentence with enough words to identify the language.", ["eng"]),
        (
            "Ceci est une phrase française qui contient assez de mots pour identifier la langue.",
            ["fra"],
        ),
        ("안녕하세요", ["kor"]),
        ("Hello", ["eng"]),
        ("", None),
        ("   ", None),
    ],
)
def test_empty_language_list_matches_automatic_detection(text, expected):
    languages = []

    result = detect_languages(text, languages=languages)

    assert result == detect_languages(text) == expected
    assert languages == []


def test_empty_language_list_uses_the_configured_short_text_fallback():
    calls = []

    def fallback(text):
        calls.append(text)
        return ["fra"]

    assert detect_languages("Bonjour", languages=[], language_fallback=fallback) == ["fra"]
    assert calls == ["Bonjour"]


@pytest.mark.parametrize("per_element", [False, True])
@pytest.mark.parametrize("iterator", [False, True])
def test_empty_language_selection_populates_real_element_metadata(per_element, iterator):
    elements = [
        NarrativeText("This document is written in English and contains several sentences."),
        NarrativeText("This second paragraph is also written in the same English language."),
    ]
    elements[0].metadata = ElementMetadata(filename="source.txt", page_number=1)
    source = iter(elements) if iterator else elements

    result = list(
        apply_lang_metadata(source, languages=[], detect_language_per_element=per_element)
    )

    assert all(actual is expected for actual, expected in zip(result, elements))
    assert [element.metadata.languages for element in result] == [["eng"], ["eng"]]
    assert result[0].metadata.filename == "source.txt"
    assert result[0].metadata.page_number == 1


@pytest.mark.parametrize(
    ("languages", "expected"),
    [(None, ["eng"]), (["auto"], ["eng"]), (["fra"], ["fra"]), ([""], None)],
)
def test_nonempty_language_options_keep_their_existing_meaning(languages, expected):
    assert detect_languages("Hello", languages=languages) == expected


@pytest.mark.parametrize("languages", ["", (), {}])
def test_invalid_empty_containers_are_still_rejected(languages):
    with pytest.raises(TypeError, match="must be a list"):
        detect_languages("Hello", languages=languages)
