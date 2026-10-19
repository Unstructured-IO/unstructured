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
def test_translate_works_with_russian():
    text = "Я тоже можно переводать русский язык!"
    assert translate.translate_text(text) == "I can also translate Russian!"


@pytest.mark.skipif(IS_CI, reason="Skipping this test in CI pipeline")
def test_translate_works_with_chinese():
    text = "網站有中、英文版本"
    assert translate.translate_text(text) == "Website available in Chinese and English"


@pytest.mark.skipif(IS_CI, reason="Skipping this test in CI pipeline")
def test_translate_works_with_arabic():
    text = "مرحباً بكم في متجرنا"
    assert translate.translate_text(text) == "Welcome to our store."


def test_translate_text_multi_chunk(monkeypatch):
    translated_inputs = []

    def mock_chunk_by_attention_window(text, tokenizer, split_function):
        return ["Chunk eins.", "Chunk zwei."]

    def mock_translate_text(text, model, tokenizer):
        translated_inputs.append(text)
        return f"Translated {text}"

    monkeypatch.setattr(translate, "chunk_by_attention_window", mock_chunk_by_attention_window)
    monkeypatch.setattr(translate, "_translate_text", mock_translate_text)
    monkeypatch.setattr(translate, "_get_opus_mt_model_name", lambda src, tgt: "mock-model")
    monkeypatch.setattr(translate.MarianTokenizer, "from_pretrained", lambda name: None)
    monkeypatch.setattr(translate.MarianMTModel, "from_pretrained", lambda name: None)

    result = translate.translate_text("Chunk eins. Chunk zwei.", source_lang="de", target_lang="en")

    assert translated_inputs == ["Chunk eins.", "Chunk zwei."]
    assert result == "Translated Chunk eins. Translated Chunk zwei."


def test_translate_text_multi_chunk_with_tokenizer_boundary(monkeypatch):
    translated_inputs = []

    class MockTokenizer:
        model_max_length = 5

        def tokenize(self, text):
            return ["token1", "token2"]

    monkeypatch.setattr(
        translate,
        "_translate_text",
        lambda chunk, model, tokenizer: translated_inputs.append(chunk) or f"Trans({chunk})",
    )
    monkeypatch.setattr(translate, "_get_opus_mt_model_name", lambda src, tgt: "mock-model")
    monkeypatch.setattr(translate.MarianTokenizer, "from_pretrained", lambda name: MockTokenizer())
    monkeypatch.setattr(translate.MarianMTModel, "from_pretrained", lambda name: None)

    text = "Erster Satz. Zweiter Satz."
    result = translate.translate_text(text, source_lang="de", target_lang="en")

    assert translated_inputs == ["Erster Satz.", "Zweiter Satz."]
    assert result == "Trans(Erster Satz.) Trans(Zweiter Satz.)"
