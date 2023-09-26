########
Embedding
########

EmbeddingEncoder classes in ``unstructured`` use document elements detected
with ``partition`` or document elements grouped with ``chunking`` to obtain
embeddings for each element, for uses cases such as Retrieval Augmented Generation (RAG).


``BaseEmbeddingEncoder``
------------------

The ``BaseEmbeddingEncoder`` is an abstract base class that defines the methods to be implemented
for each ``EmbeddingEncoder`` subclass.


``OpenAIEmbeddingEncoder``
------------------

The ``OpenAIEmbeddingEncoder`` class uses langchain OpenAI integration under the hood
to connect to the OpenAI Text&Embedding API to obtain embeddings for pieces of text.

``embed_documents`` will receive a list of Elements, and return an updated list which
includes the ``embeddings`` attribute for each Element.

``embed_query`` will receive a query as a string, and return a list of floats which is the
embedding vector for the given query string.

``num_of_dimensions`` is a metadata property that denotes the number of dimensions in any
embedding vector obtained via this class.

``is_unit_vector`` is a metadata property that denotes if embedding vectors obtained via
this class are unit vectors.

The following code block shows an example of how to use ``OpenAIEmbeddingEncoder``. You will
see the updated elements list (with the ``embeddings`` attribute included for each element),
the embedding vector for the query string, and some metadata properties about the embedding model.
You will need to set an environment variable named ``OPENAI_API_KEY`` to be able to run this example.
To obtain an api key, visit: https://platform.openai.com/account/api-keys

.. code:: python

    import os

    from unstructured.documents.elements import Text
    from unstructured.embed.openai import OpenAIEmbeddingEncoder

    embedding_encoder = OpenAIEmbeddingEncoder(api_key=os.environ["OPENAI_API_KEY"])
    elements = embedding_encoder.embed_documents(
        elements=[Text("This is sentence 1"), Text("This is sentence 2")],
    )

    query = "This is the query"
    query_embedding = embedding_encoder.embed_query(query=query)

    [print(e.embeddings, e) for e in elements]
    print(query_embedding, query)
    print(embedding_encoder.is_unit_vector(), embedding_encoder.num_of_dimensions())
