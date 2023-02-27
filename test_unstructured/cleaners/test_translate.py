import pytest

from unstructured.cleaners import translate


def test_get_opus_mt_model_name():
    model_name = translate._get_opus_mt_model_name("ru", "en")
    assert model_name == "Helsinki-NLP/opus-mt-ru-en"


@pytest.mark.parametrize("code", ["way-too-long", "a", "", None])
def test_validate_language_code(code):
    with pytest.raises(ValueError):
        translate._validate_language_code(code)


def test_translate_returns_same_text_if_dest_is_same():
    text = "This is already in English!"
    assert translate.translate_text(text, "en", "en") == text


def test_translate_returns_same_text_text_is_empty():
    text = "      "
    assert translate.translate_text(text) == text


def test_translate_with_language_specified():
    text = "Ich bin ein Berliner!"
    assert translate.translate_text(text, "de") == "I'm a Berliner!"


def test_translate_with_no_language_specified():
    text = "Ich bin ein Berliner!"
    assert translate.translate_text(text) == "I'm a Berliner!"


def test_translate_raises_with_bad_language():
    text = "Ich bin ein Berliner!"
    with pytest.raises(ValueError):
        translate.translate_text(text, "zz")


def test_tranlate_works_with_russian():
    text = "Я тоже можно переводать русский язык!"
    assert translate.translate_text(text) == "I can also translate Russian!"


def test_translate_works_with_chinese():
    text = "網站有中、英文版本"
    translate.translate_text(text) == "Website available in Chinese and English"


def translate_works_with_arabic():
    text = "مرحباً بكم في متجرنا"
    translate.translate_text(text) == "Welcome to our store."
