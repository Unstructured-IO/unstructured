import pytest

from unstructured.partition import lang


def test_prepare_languages_for_tesseract_with_one_language():
    languages = ["en"]
    assert lang.prepare_languages_for_tesseract(languages) == "eng"


def test_prepare_languages_for_tesseract_special_case():
    languages = ["osd"]
    assert lang.prepare_languages_for_tesseract(languages) == "osd"

    languages = ["equ"]
    assert lang.prepare_languages_for_tesseract(languages) == "equ"


def test_prepare_languages_for_tesseract_removes_empty_inputs():
    languages = ["kbd", "es"]
    assert lang.prepare_languages_for_tesseract(languages) == "spa+spa_old"


def test_prepare_languages_for_tesseract_includes_variants():
    languages = ["chi"]
    assert (
        lang.prepare_languages_for_tesseract(languages)
        == "chi_sim+chi_sim_vert+chi_tra+chi_tra_vert"
    )


def test_prepare_languages_for_tesseract_with_multiple_languages():
    languages = ["ja", "afr", "en", "equ"]
    assert lang.prepare_languages_for_tesseract(languages) == "jpn+jpn_vert+afr+eng+equ"


def test_prepare_languages_for_tesseract_warns_nonstandard_language(caplog):
    languages = ["zzz", "chi"]
    assert (
        lang.prepare_languages_for_tesseract(languages)
        == "chi_sim+chi_sim_vert+chi_tra+chi_tra_vert"
    )
    assert "not a valid standard language code" in caplog.text


def test_prepare_languages_for_tesseract_warns_non_tesseract_language(caplog):
    languages = ["kbd", "eng"]
    assert lang.prepare_languages_for_tesseract(languages) == "eng"
    assert "not a language supported by Tesseract" in caplog.text


def test_detect_languages_english_auto():
    text = "This is a short sentence."
    assert lang.detect_languages(text) == ["eng"]


def test_detect_languages_english_provided():
    text = "This is another short sentence."
    languages = ["en"]
    assert lang.detect_languages(text, languages) == ["eng"]


def test_detect_languages_korean_auto():
    text = "안녕하세요"
    assert lang.detect_languages(text) == ["kor"]


def test_detect_languages_gets_multiple_languages():
    text = "My lubimy mleko i chleb."
    assert lang.detect_languages(text) == ["ces", "pol", "slk"]


def test_detect_languages_warns_for_auto_and_other_input(caplog):
    text = "This is another short sentence."
    languages = ["en", "auto", "rus"]
    assert lang.detect_languages(text, languages) == ["eng"]
    assert "rest of the inputted languages will be ignored" in caplog.text


def test_detect_languages_raises_TypeError_for_invalid_languages():
    with pytest.raises(TypeError):
        text = "This is a short sentence."
        lang.detect_languages(text, languages="eng") == ["eng"]
