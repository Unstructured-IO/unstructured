# pyright: reportPrivateUsage=false

"""Unit-test suite for the `unstructured.partition.lang` module."""

from __future__ import annotations

import os
import pathlib
from typing import Union

import pytest

from unstructured.documents.elements import (
    NarrativeText,
    PageBreak,
)
from unstructured.partition.lang import (
    _clean_ocr_languages_arg,
    _convert_language_code_to_pytesseract_lang_code,
    apply_lang_metadata,
    check_language_args,
    detect_languages,
    prepare_languages_for_tesseract,
    tesseract_to_paddle_language,
)

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "..", "example-docs")


def test_prepare_languages_for_tesseract_with_one_language():
    languages = ["en"]
    assert prepare_languages_for_tesseract(languages) == "eng"


def test_prepare_languages_for_tesseract_with_duplicated_languages():
    languages = ["en", "eng"]
    assert prepare_languages_for_tesseract(languages) == "eng"


def test_prepare_languages_for_tesseract_special_case():
    languages = ["osd"]
    assert prepare_languages_for_tesseract(languages) == "osd"

    languages = ["equ"]
    assert prepare_languages_for_tesseract(languages) == "equ"


def test_prepare_languages_for_tesseract_removes_empty_inputs():
    languages = ["kbd", "es"]
    assert prepare_languages_for_tesseract(languages) == "spa+spa_old"


def test_prepare_languages_for_tesseract_includes_variants():
    languages = ["chi"]
    assert prepare_languages_for_tesseract(languages) == "chi_sim+chi_sim_vert+chi_tra+chi_tra_vert"


def test_prepare_languages_for_tesseract_with_multiple_languages():
    languages = ["ja", "afr", "en", "equ"]
    assert prepare_languages_for_tesseract(languages) == "jpn+jpn_vert+afr+eng+equ"


def test_prepare_languages_for_tesseract_warns_nonstandard_language(caplog):
    languages = ["zzz", "chi"]
    assert prepare_languages_for_tesseract(languages) == "chi_sim+chi_sim_vert+chi_tra+chi_tra_vert"
    assert "not a valid standard language code" in caplog.text


def test_prepare_languages_for_tesseract_warns_non_tesseract_language(caplog):
    languages = ["kbd", "eng"]
    assert prepare_languages_for_tesseract(languages) == "eng"
    assert "not a language supported by Tesseract" in caplog.text


def test_prepare_languages_for_tesseract_None_languages():
    with pytest.raises(ValueError, match="`languages` can not be `None`"):
        languages = None
        prepare_languages_for_tesseract(languages)


def test_prepare_languages_for_tesseract_no_valid_languages(caplog):
    languages = [""]
    assert prepare_languages_for_tesseract(languages) == "eng"
    assert "Failed to find any valid standard language code from languages" in caplog.text


@pytest.mark.parametrize(
    ("tesseract_lang", "expected_lang"),
    [
        ("eng", "en"),
        ("chi_sim", "ch"),
        ("chi_tra", "chinese_cht"),
        ("deu", "german"),
        ("jpn", "japan"),
        ("kor", "korean"),
    ],
)
def test_tesseract_to_paddle_language_valid_codes(tesseract_lang, expected_lang):
    assert expected_lang == tesseract_to_paddle_language(tesseract_lang)


def test_tesseract_to_paddle_language_invalid_codes(caplog):
    tesseract_lang = "unsupported_lang"
    assert tesseract_to_paddle_language(tesseract_lang) == "en"
    assert "unsupported_lang is not a language code supported by PaddleOCR," in caplog.text


@pytest.mark.parametrize(
    ("tesseract_lang", "expected_lang"),
    [
        ("ENG", "en"),
        ("Fra", "fr"),
        ("DEU", "german"),
    ],
)
def test_tesseract_to_paddle_language_case_sensitivity(tesseract_lang, expected_lang):
    assert expected_lang == tesseract_to_paddle_language(tesseract_lang)


def test_detect_languages_english_auto():
    text = "This is a short sentence."
    assert detect_languages(text) == ["eng"]


def test_detect_languages_english_provided():
    text = "This is another short sentence."
    languages = ["en"]
    assert detect_languages(text, languages) == ["eng"]


def test_detect_languages_korean_auto():
    text = "안녕하세요"
    assert detect_languages(text) == ["kor"]


def test_detect_languages_gets_multiple_languages():
    text = "My lubimy mleko i chleb."
    assert detect_languages(text) == ["ces", "pol", "slk"]


def test_detect_languages_warns_for_auto_and_other_input(caplog):
    text = "This is another short sentence."
    languages = ["en", "auto", "rus"]
    assert detect_languages(text, languages) == ["eng"]
    assert "rest of the inputted languages will be ignored" in caplog.text


def test_detect_languages_raises_TypeError_for_invalid_languages():
    with pytest.raises(TypeError):
        text = "This is a short sentence."
        detect_languages(text, languages="eng") == ["eng"]


def test_apply_lang_metadata_has_no_warning_for_PageBreak(caplog):
    elements = [NarrativeText("Sample text."), PageBreak("")]
    elements = list(
        apply_lang_metadata(
            elements=elements,
            languages=["auto"],
            detect_language_per_element=True,
        ),
    )
    assert "No features in text." not in [rec.message for rec in caplog.records]


@pytest.mark.parametrize(
    ("lang_in", "expected_lang"),
    [
        ("en", "eng"),
        ("fr", "fra"),
    ],
)
def test_convert_language_code_to_pytesseract_lang_code(lang_in, expected_lang):
    assert expected_lang == _convert_language_code_to_pytesseract_lang_code(lang_in)


@pytest.mark.parametrize(
    ("input_ocr_langs", "expected"),
    [
        (["eng"], "eng"),  # list
        ('"deu"', "deu"),  # extra quotation marks
        ("[deu]", "deu"),  # brackets
        ("['deu']", "deu"),  # brackets and quotation marks
        (["[deu]"], "deu"),  # list, brackets and quotation marks
        (['"deu"'], "deu"),  # list and quotation marks
        ("deu+spa", "deu+spa"),  # correct input
    ],
)
def test_clean_ocr_languages_arg(input_ocr_langs, expected):
    assert _clean_ocr_languages_arg(input_ocr_langs) == expected


def test_detect_languages_handles_spelled_out_languages():
    languages = detect_languages(text="Sample text longer than 5 words.", languages=["Spanish"])
    assert languages == ["spa"]


@pytest.mark.parametrize(
    ("languages", "ocr_languages", "expected_langs"),
    [
        (["spa"], "deu", ["spa"]),
        (["spanish"], "english", ["spa"]),
        (["spa"], "[deu]", ["spa"]),
        (["spa"], '"deu"', ["spa"]),
        (["spa"], ["deu"], ["spa"]),
        (["spa"], ["[deu]"], ["spa"]),
        (["spa+deu"], "eng+deu", ["spa", "deu"]),
    ],
)
def test_check_language_args_uses_languages_when_ocr_languages_and_languages_are_both_defined(
    languages: Union[list[str], str],
    ocr_languages: Union[list[str], str, None],
    expected_langs: list[str],
    caplog,
):
    returned_langs = check_language_args(languages=languages, ocr_languages=ocr_languages)
    for lang in returned_langs:  # type: ignore
        assert lang in expected_langs
        assert "ocr_languages" in caplog.text


@pytest.mark.parametrize(
    ("languages", "ocr_languages", "expected_langs"),
    [
        # raise warning and use `ocr_languages` when `languages` is empty or None
        ([], "deu", ["deu"]),
        ([""], '"deu"', ["deu"]),
        ([""], "deu", ["deu"]),
        ([""], "[deu]", ["deu"]),
    ],
)
def test_check_language_args_uses_ocr_languages_when_languages_is_empty_or_None(
    languages: Union[list[str], str],
    ocr_languages: Union[list[str], str, None],
    expected_langs: list[str],
    caplog,
):
    returned_langs = check_language_args(languages=languages, ocr_languages=ocr_languages)
    for lang in returned_langs:  # type: ignore
        assert lang in expected_langs
        assert "ocr_languages" in caplog.text


@pytest.mark.parametrize(
    ("languages", "ocr_languages"),
    [
        ([], None),  # how check_language_args is called from auto.partition()
        ([""], None),
    ],
)
def test_check_language_args_returns_None(
    languages: Union[list[str], str, None],
    ocr_languages: Union[list[str], str, None],
):
    returned_langs = check_language_args(languages=languages, ocr_languages=ocr_languages)
    assert returned_langs is None


def test_check_language_args_returns_auto(
    languages=["eng", "spa", "auto"],
    ocr_languages=None,
):
    returned_langs = check_language_args(languages=languages, ocr_languages=ocr_languages)
    assert returned_langs == ["auto"]


@pytest.mark.parametrize(
    ("languages", "ocr_languages"),
    [
        ([], ["auto"]),
        ([""], "eng+auto"),
    ],
)
def test_check_language_args_raises_error_when_ocr_languages_contains_auto(
    languages: Union[list[str], str, None],
    ocr_languages: Union[list[str], str, None],
):
    with pytest.raises(ValueError):
        check_language_args(languages=languages, ocr_languages=ocr_languages)
