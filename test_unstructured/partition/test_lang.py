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
