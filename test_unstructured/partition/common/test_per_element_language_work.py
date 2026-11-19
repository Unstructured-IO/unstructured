"""Verify per-element language detection does not process a discarded document sample."""

import pytest

from unstructured.documents.elements import NarrativeText, PageBreak
from unstructured.partition.common import lang


@pytest.mark.parametrize("languages", [None, [], ["auto"], ["fra"]])
@pytest.mark.parametrize("use_iterator", [False, True])
def test_per_element_mode_only_detects_each_element(languages, use_iterator, monkeypatch):
    elements = [NarrativeText("First heading"), NarrativeText("Second heading"), PageBreak("")]
    detected_texts = []
    detect = lang.detect_languages

    def record_detection(text, **kwargs):
        detected_texts.append(text)
        return detect(text, **kwargs)

    monkeypatch.setattr(lang, "detect_languages", record_detection)
    result = list(
        lang.apply_lang_metadata(
            iter(elements) if use_iterator else elements,
            languages=languages,
            detect_language_per_element=True,
        )
    )

    assert len(result) == len(elements)
    assert all(actual is original for actual, original in zip(result, elements))
    expected = ["fra"] if languages == ["fra"] else ["eng"]
    assert [element.metadata.languages for element in result] == [expected, expected, None]
    assert detected_texts == ["First heading", "Second heading", ""]


def test_custom_fallback_receives_only_the_individual_element_texts():
    seen = []

    def fallback(text):
        seen.append(text)
        return ["fra"]

    elements = [NarrativeText("Hello"), NarrativeText("World")]
    result = list(
        lang.apply_lang_metadata(
            elements,
            languages=["auto"],
            detect_language_per_element=True,
            language_fallback=fallback,
        )
    )

    assert [element.metadata.languages for element in result] == [["fra"], ["fra"]]
    assert seen == ["Hello", "World"]


def test_empty_per_element_input_does_not_run_detection(monkeypatch):
    detected_texts = []
    detect = lang.detect_languages

    def record_detection(text, **kwargs):
        detected_texts.append(text)
        return detect(text, **kwargs)

    monkeypatch.setattr(lang, "detect_languages", record_detection)

    assert (
        list(lang.apply_lang_metadata([], languages=None, detect_language_per_element=True)) == []
    )
    assert detected_texts == []


@pytest.mark.parametrize("languages", [None, ["fra"]])
def test_document_mode_still_detects_one_combined_sample(languages, monkeypatch):
    detected_texts = []
    detect = lang.detect_languages

    def record_detection(text, **kwargs):
        detected_texts.append(text)
        return detect(text, **kwargs)

    monkeypatch.setattr(lang, "detect_languages", record_detection)
    elements = [NarrativeText("First heading"), NarrativeText("Second heading")]

    result = list(lang.apply_lang_metadata(elements, languages=languages))

    expected = ["fra"] if languages else ["eng"]
    assert [element.metadata.languages for element in result] == [expected, expected]
    assert detected_texts == ["First heading Second heading"]


def test_disabled_detection_retains_existing_metadata():
    element = NarrativeText("Hello")
    element.metadata.languages = ["deu"]

    assert list(
        lang.apply_lang_metadata([element], languages=[""], detect_language_per_element=True)
    ) == [element]
    assert element.metadata.languages == ["deu"]
