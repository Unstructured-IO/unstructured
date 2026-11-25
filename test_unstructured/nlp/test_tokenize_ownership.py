from types import SimpleNamespace

import pytest

from unstructured.nlp import tokenize


@pytest.mark.parametrize("tokenizer", [tokenize.word_tokenize, tokenize.pos_tag])
def test_a_caller_cannot_mutate_a_cached_tokenization(tokenizer, monkeypatch):
    tokenizer.cache_clear()
    calls = []

    def process(text):
        calls.append(text)
        return [SimpleNamespace(text="Hello", tag_="UH"), SimpleNamespace(text="!", tag_=".")]

    monkeypatch.setattr(tokenize, "_process", process)
    try:
        first = tokenizer("Hello!")
        expected = first.copy()
        first.clear()

        second = tokenizer("Hello!")

        assert second == expected
        assert second is not first
        assert calls == ["Hello!"]
        assert tokenizer.cache_info().hits == 1
        second.append("caller-owned")
        assert tokenizer("Hello!") == expected
    finally:
        tokenizer.cache_clear()
