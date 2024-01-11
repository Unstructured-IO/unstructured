Data Processing into Vector Database
====================================

Introduction
------------

In this guide, we demonstrate how to leverage Unstructured.IO, ChromaDB, and LangChain to summarize topics from the front page of CNN Lite. Utilizing the modern LLM stack, including Unstructured, Chroma, and LangChain, this workflow is streamlined to less than two dozen lines of code.

Gather Links with Unstructured
------------------------------

First, we gather links from the CNN Lite homepage using the `partition_html` function from Unstructured. When Unstructured partitions HTML pages, links are included in the metadata for each element, making link collection straightforward.

.. code-block:: python

    from unstructured.partition.html import partition_html

    cnn_lite_url = "https://lite.cnn.com/"
    elements = partition_html(url=cnn_lite_url)
    links = []

    for element in elements:
        if element.metadata.links is not None:
            relative_link = element.metadata.links[0]["url"][1:]
            if relative_link.startswith("2023"):
                links.append(f"{cnn_lite_url}{relative_link}")

Ingest Individual Articles with UnstructuredURLLoader
-----------------------------------------------------

With the links in hand, we preprocess individual news articles using UnstructuredURLLoader. This loader fetches content from the web and then uses the unstructured partition function to extract content and metadata. Here we preprocess HTML files, but it also works with other response types like `application/pdf`. The result is a list of LangChain Document objects.

.. code-block:: python

    from langchain.document_loaders import UnstructuredURLLoader

    loaders = UnstructuredURLLoader(urls=links, show_progress_bar=True)
    docs = loaders.load()

Load Documents into ChromaDB
-----------------------------

The next step is to load the preprocessed documents into ChromaDB. This process involves vectorizing the documents using OpenAI embeddings and loading them into Chroma's vector store. Once in Chroma, similarity search can be performed to retrieve documents related to specific topics.

.. code-block:: python

    from langchain.vectorstores.chroma import Chroma
    from langchain.embeddings import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(docs, embeddings)
    query_docs = vectorstore.similarity_search("Update on the coup in Niger.", k=1)

Summarize the Documents
-----------------------

After retrieving relevant documents from Chroma, we summarize them using LangChain. The `load_summarization_chain` function allows for easy summarization, simply requiring the selection of an LLM and summarization chain.

.. code-block:: python

    from langchain.chat_models import ChatOpenAI
    from langchain.chains.summarize import load_summarize_chain

    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-16k")
    chain = load_summarize_chain(llm, chain_type="stuff")
    chain.run(query_docs)

Jupyter Notebook
-----------------

To delve deeper into this example, you can access the full Jupyter Notebook here: `News of the Day Notebook <https://github.com/Unstructured-IO/unstructured/blob/main/examples/chroma-news-of-the-day/news-of-the-day.ipynb>`_
