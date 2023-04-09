import pytest

from unstructured.documents.elements import Text, Title
from unstructured.staging import huggingface


class MockTokenizer:
    model_max_length = 20

    def tokenize(self, text):
        return text.split(" ")


def test_stage_for_transformers():
    title_element = (Title(text="Here is a wonderful story"),)
    elements = [title_element, Text(text="hello " * 20 + "there " * 20)]

    tokenizer = MockTokenizer()

    chunk_elements = huggingface.stage_for_transformers(elements, tokenizer, buffer=10)

    hello_chunk = Text(("hello " * 10).strip())
    there_chunk = Text(("there " * 10).strip())

    assert chunk_elements == [
        title_element,
        hello_chunk,
        hello_chunk,
        there_chunk,
        there_chunk,
    ]


def test_chunk_by_attention_window():
    text = "hello " * 20 + "there " * 20
    tokenizer = MockTokenizer()
    chunks = huggingface.chunk_by_attention_window(text, tokenizer, buffer=10)

    hello_chunk = ("hello " * 10).strip()
    there_chunk = ("there " * 10).strip()
    assert chunks == [hello_chunk, hello_chunk, there_chunk, there_chunk]


def test_chunk_by_attention_window_no_buffer():
    text = "hello " * 20 + "there " * 20
    tokenizer = MockTokenizer()
    chunks = huggingface.chunk_by_attention_window(text, tokenizer, buffer=0)

    hello_chunk = ("hello " * 20).strip()
    there_chunk = ("there " * 20).strip()
    assert chunks == [hello_chunk, there_chunk]


def test_chunk_by_attention_window_raises_with_negative_buffer():
    text = "hello " * 20 + "there " * 20
    tokenizer = MockTokenizer()
    with pytest.raises(ValueError):
        huggingface.chunk_by_attention_window(text, tokenizer, buffer=-10)


def test_chunk_by_attention_window_raises_if_buffer_too_big():
    text = "hello " * 20 + "there " * 20
    tokenizer = MockTokenizer()
    with pytest.raises(ValueError):
        # NOTE(robinson) - The buffer exceeds the max input size of 20
        huggingface.chunk_by_attention_window(text, tokenizer, buffer=40)


def test_chunk_by_attention_window_raises_if_chunk_exceeds_window():
    text = "hello " * 100 + "."
    tokenizer = MockTokenizer()
    with pytest.raises(ValueError):

        def split_function(text):
            return text.split(".")

        huggingface.chunk_by_attention_window(text, tokenizer, split_function=split_function)
