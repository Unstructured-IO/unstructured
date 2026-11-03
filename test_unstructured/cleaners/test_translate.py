import os

import pytest

from unstructured.cleaners import translate

IS_CI = os.getenv("CI") == "true"


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


@pytest.mark.skipif(IS_CI, reason="Skipping this test in CI pipeline")
def test_translate_with_language_specified():
    text = "Ich bin ein Berliner!"
    assert translate.translate_text(text, "de") == "I'm a Berliner!"


@pytest.mark.skipif(IS_CI, reason="Skipping this test in CI pipeline")
def test_translate_with_no_language_specified():
    text = "Ich bin ein Berliner!"
    assert translate.translate_text(text) == "I'm a Berliner!"


@pytest.mark.skipif(IS_CI, reason="Skipping this test in CI pipeline")
def test_translate_raises_with_bad_language():
    text = "Ich bin ein Berliner!"
    with pytest.raises(ValueError):
        translate.translate_text(text, "zz")


@pytest.mark.skipif(IS_CI, reason="Skipping this test in CI pipeline")
def test_tranlate_works_with_russian():
    text = "Я тоже можно переводать русский язык!"
    assert translate.translate_text(text) == "I can also translate Russian!"


@pytest.mark.skipif(IS_CI, reason="Skipping this test in CI pipeline")
def test_translate_works_with_chinese():
    text = "網站有中、英文版本"
    translate.translate_text(text) == "Website available in Chinese and English"


def translate_works_with_arabic():
    text = "مرحباً بكم في متجرنا"
    translate.translate_text(text) == "Welcome to our store."


class FakeMarianTokenizer:
    """Whitespace tokenizer with an attention window that only fits a single short sentence."""

    model_max_length = 8

    def tokenize(self, text):
        return text.split()

    def __call__(self, texts, **kwargs):
        return {"input_ids": texts}

    def decode(self, token_ids, **kwargs):
        return token_ids


class FakeMarianModel:
    """Records the text it is asked to translate and "translates" it by upper-casing it."""

    def __init__(self):
        self.inputs = []

    def generate(self, input_ids):
        self.inputs.extend(input_ids)
        return [text.upper() for text in input_ids]


def test_translate_translates_each_chunk_of_text_longer_than_the_attention_window(monkeypatch):
    sentences = [
        "This is the first sentence.",
        "This is the second sentence.",
        "This is the third sentence.",
    ]
    text = " ".join(sentences)
    model = FakeMarianModel()
    monkeypatch.setattr(
        translate.MarianTokenizer, "from_pretrained", lambda model_name: FakeMarianTokenizer()
    )
    monkeypatch.setattr(translate.MarianMTModel, "from_pretrained", lambda model_name: model)

    translated_text = translate.translate_text(text, "en", "de")

    assert model.inputs == sentences
    assert translated_text == text.upper()
