import unstructured.staging.huggingface as huggingface


class MockTokenizer:

    model_max_length = 20

    def tokenize(self, text):
        return text.split(" ")


def test_chunk_by_attention_window():
    text = "hello " * 20 + "there " * 20
    tokenizer = MockTokenizer()
    chunks = huggingface.chunk_by_attention_window(text, tokenizer, buffer=10)

    hello_chunk = ("hello " * 10).strip()
    there_chunk = ("there " * 10).strip()
    assert chunks == [hello_chunk, hello_chunk, there_chunk, there_chunk]
