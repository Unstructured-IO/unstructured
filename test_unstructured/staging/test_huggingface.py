import pytest
from tokenizers import Tokenizer, models, pre_tokenizers
from transformers import PreTrainedTokenizerFast

from unstructured.documents.elements import ElementMetadata, Text, Title
from unstructured.staging import huggingface


class MockTokenizer:
    model_max_length = 20

    def tokenize(self, text):
        return text.split(" ")


@pytest.fixture
def character_tokenizer():
    backend = Tokenizer(
        models.BPE(
            vocab={"[UNK]": 0, "a": 1, "b": 2, "c": 3, "Ġ": 4, "|": 5},
            merges=[],
            unk_token="[UNK]",
        )
    )
    backend.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    return PreTrainedTokenizerFast(tokenizer_object=backend, unk_token="[UNK]")


@pytest.mark.parametrize(
    ("separator", "max_input_size", "buffer", "expected"),
    [
        (" ", 3, 0, ["a b", "c"]),
        (" ", 4, 1, ["a b", "c"]),
        (" | ", 5, 0, ["a | b", "c"]),
        ("", 2, 0, ["ab", "c"]),
    ],
)
def test_chunk_by_attention_window_counts_joined_text(
    character_tokenizer, separator, max_input_size, buffer, expected
):
    chunks = huggingface.chunk_by_attention_window(
        "a b c",
        character_tokenizer,
        max_input_size=max_input_size,
        buffer=buffer,
        chunk_separator=separator,
    )

    assert chunks == expected
    assert all(
        len(character_tokenizer.tokenize(chunk)) <= max_input_size - buffer for chunk in chunks
    )


def test_stage_for_transformers_respects_joined_token_budget(character_tokenizer):
    source = Text("a b c", metadata=ElementMetadata(filename="source.txt"))

    chunks = huggingface.stage_for_transformers(
        [source], character_tokenizer, max_input_size=3, buffer=0
    )

    assert [chunk.text for chunk in chunks] == ["a b", "c"]
    assert all(len(character_tokenizer.tokenize(chunk.text)) <= 3 for chunk in chunks)
    assert all(chunk.metadata.filename == "source.txt" for chunk in chunks)
    assert source.text == "a b c"


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
