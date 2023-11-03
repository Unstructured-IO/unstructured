#########
Embedding
#########

Embedding encoder classes in ``unstructured`` use document elements detected
with ``partition`` or document elements grouped with ``chunking`` to obtain
embeddings for each element, for uses cases such as Retrieval Augmented Generation (RAG).


``BaseEmbeddingEncoder``
------------------------

The ``BaseEmbeddingEncoder`` is an abstract base class that defines the methods to be implemented
for each ``EmbeddingEncoder`` subclass.


``OpenAIEmbeddingEncoder``
--------------------------

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

    # Initialize the encoder with OpenAI credentials
    embedding_encoder = OpenAIEmbeddingEncoder(api_key=os.environ["OPENAI_API_KEY"])

    # Embed a list of Elements
    elements = embedding_encoder.embed_documents(
        elements=[Text("This is sentence 1"), Text("This is sentence 2")],
    )

    # Embed a single query string
    query = "This is the query"
    query_embedding = embedding_encoder.embed_query(query=query)

    # Print embeddings
    [print(e.embeddings, e) for e in elements]
    print(query_embedding, query)
    print(embedding_encoder.is_unit_vector(), embedding_encoder.num_of_dimensions())

``HuggingFaceEmbeddingEncoder``
---------------------------------

The ``HuggingFaceEmbeddingEncoder`` class uses langchain HuggingFace integration under the hood
to obtain embeddings for pieces of text using a local model.

``embed_documents`` will receive a list of Elements, and return an updated list which
includes the ``embeddings`` attribute for each Element.

``embed_query`` will receive a query as a string, and return a list of floats which is the
embedding vector for the given query string.

``num_of_dimensions`` is a metadata property that denotes the number of dimensions in any
embedding vector obtained via this class.

``is_unit_vector`` is a metadata property that denotes if embedding vectors obtained via
this class are unit vectors.

The following code block shows an example of how to use ``HuggingFaceEmbeddingEncoder``. You will
see the updated elements list (with the ``embeddings`` attribute included for each element),
the embedding vector for the query string, and some metadata properties about the embedding model.


``BedrockEmbeddingEncoder``
-----------------------------

The ``BedrockEmbeddingEncoder`` class provides an interface to obtain embeddings for text using the Bedrock embeddings via the langchain integration. It connects to the Bedrock Runtime using AWS's boto3 package.

Key methods and attributes include:

``embed_documents``: This function takes a list of Elements as its input and returns the same list with an updated embeddings attribute for each Element.

``embed_query``: This method takes a query as a string and returns the embedding vector for the given query string.

``num_of_dimensions``: A metadata property that signifies the number of dimensions in any embedding vector obtained via this class.

``is_unit_vector``: A metadata property that checks if embedding vectors obtained via this class are unit vectors.

Initialization:
To create an instance of the `BedrockEmbeddingEncoder`, AWS credentials and the region name are required.

.. code:: python

    from unstructured.documents.elements import Text
    from unstructured.embed.bedrock import BedrockEmbeddingEncoder

    # Initialize the encoder with AWS credentials
    embedding_encoder = BedrockEmbeddingEncoder(
        aws_access_key_id="YOUR_AWS_ACCESS_KEY_ID",
        aws_secret_access_key="YOUR_AWS_SECRET_ACCESS_KEY",
        region_name="us-west-2",
    )

    # Embed a list of Elements
    elements = embedding_encoder.embed_documents(elements=[Text("Sentence A"), Text("Sentence B")])

    # Embed a single query string
    query = "Example query"
    query_embedding = embedding_encoder.embed_query(query=query)

    # Print embeddings
    [print(e.embeddings, e) for e in elements]
    print(query_embedding, query)
    print(embedding_encoder.is_unit_vector(), embedding_encoder.num_of_dimensions())


Dependencies:
This class relies on several dependencies which include boto3, numpy, and langchain. Ensure these are installed and available in the environment where this class is utilized.
