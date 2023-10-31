import numpy as np

from unstructured.documents.elements import Text
from unstructured.embed.huggingface import HuggingFaceEmbeddingEncoder


def embed_documents_does_not_break_element_to_dict():
    try:
        encoder = HuggingFaceEmbeddingEncoder()

        doc_embed_result = encoder.embed_documents(
            elements=[Text("This is sentence 1"), Text("This is sentence 2")],
        )
        query_embed_result = encoder.embed_query(Text("This is sentence 1"))

        # Keep the number of elements same
        assert len(doc_embed_result) == 2

        # Have consistent embedding dimensionality
        assert (
            len(doc_embed_result[0].embeddings)
            == len(doc_embed_result[1].embeddings)
            == len(query_embed_result)
            == 384
        )

        # Keep element text the same
        assert doc_embed_result[0].to_dict()["text"] == "This is sentence 1"
        assert doc_embed_result[1].to_dict()["text"] == "This is sentence 2"

        # Generate reproducable / deterministic embeddings
        assert all(
            np.isclose(
                doc_embed_result[0].embeddings[:5],
                [
                    0.0356232188642025,
                    0.06595201045274734,
                    0.06317725777626038,
                    0.04989251494407654,
                    0.0425567664206028,
                ],
            ),
        )

        assert all(
            np.isclose(
                doc_embed_result[1].embeddings[:5],
                [
                    0.0622941255569458,
                    0.0793377012014389,
                    0.05761214718222618,
                    0.0711262971162796,
                    0.05167127028107643,
                ],
            ),
        )

        assert all(
            np.isclose(
                query_embed_result[:5],
                [
                    0.03562326729297638,
                    0.06595207005739212,
                    0.0631771832704544,
                    0.04989247024059296,
                    0.04255683720111847,
                ],
            ),
        )
        return True

    except AssertionError:
        return False


if __name__ == "__main__":
    print(embed_documents_does_not_break_element_to_dict())
