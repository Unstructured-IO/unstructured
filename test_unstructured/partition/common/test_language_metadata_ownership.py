import pytest

from unstructured.documents.elements import ElementMetadata, NarrativeText, PageBreak
from unstructured.partition.common.lang import apply_lang_metadata
from unstructured.staging.base import elements_to_dicts


@pytest.mark.parametrize("languages", [["eng"], ["auto"], None, []])
@pytest.mark.parametrize("as_iterator", [False, True])
def test_correcting_one_elements_language_does_not_change_other_elements(languages, as_iterator):
    elements = [
        NarrativeText(
            "This document is written in English and contains several detailed paragraphs.",
            metadata=ElementMetadata(filename="source.txt", page_number=1),
        ),
        NarrativeText("The following paragraph is also written in the same English language."),
        PageBreak(""),
    ]
    source = iter(elements) if as_iterator else elements

    result = list(apply_lang_metadata(source, languages=languages))
    result[0].metadata.languages.append("fra")

    assert all(actual is expected for actual, expected in zip(result, elements))
    assert [element.metadata.languages for element in result] == [["eng", "fra"], ["eng"], ["eng"]]
    assert [item["metadata"]["languages"] for item in elements_to_dicts(result)] == [
        ["eng", "fra"],
        ["eng"],
        ["eng"],
    ]
    result[1].metadata.languages.clear()
    assert result[0].metadata.languages == ["eng", "fra"]
    assert result[2].metadata.languages == ["eng"]
    assert result[0].metadata.filename == "source.txt"
    assert result[0].metadata.page_number == 1


def test_short_text_fallback_languages_are_independent_for_each_element():
    fallback_value = ["fra"]
    elements = [NarrativeText("Hi."), NarrativeText("Hello.")]

    result = list(
        apply_lang_metadata(
            elements, languages=["auto"], language_fallback=lambda _: fallback_value
        )
    )
    result[0].metadata.languages[0] = "eng"

    assert result[1].metadata.languages == ["fra"]
    assert fallback_value == ["fra"]


def test_per_element_detection_keeps_its_existing_independent_languages():
    elements = [NarrativeText("Hi."), NarrativeText("Hello."), PageBreak("")]

    result = list(
        apply_lang_metadata(elements, languages=["eng"], detect_language_per_element=True)
    )
    result[0].metadata.languages.append("fra")

    assert [element.metadata.languages for element in result] == [["eng", "fra"], ["eng"], None]


def test_disabling_detection_preserves_existing_language_values():
    elements = [
        NarrativeText("Hello", metadata=ElementMetadata(languages=["eng"])),
        NarrativeText("Bonjour", metadata=ElementMetadata(languages=["fra"])),
    ]
    originals = [element.metadata.languages for element in elements]

    result = list(apply_lang_metadata(iter(elements), languages=[""]))

    assert all(
        element.metadata.languages is original for element, original in zip(result, originals)
    )
    assert [element.metadata.languages for element in result] == [["eng"], ["fra"]]


def test_empty_input_still_produces_no_elements():
    assert list(apply_lang_metadata([], languages=["eng"])) == []
