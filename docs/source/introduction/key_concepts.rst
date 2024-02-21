Key Concepts
============

Natural Language Processing (NLP) encompasses various tasks and methodologies. This section introduces fundamental concepts crucial for most NLP projects involving Unstructured products.

Data Ingestion
**************

Unstructured ``Source Connectors`` make data ingestion easy. They ensure that your data is accessible, up to date, and usable for any downstream task. If you'd like to read more on our source connectors, you can find details `here <https://unstructured-io.github.io/unstructured/ingest/source_connectors.html>`__.

Data Preprocessing
******************

Before the core analysis, raw data often requires significant preprocessing:

- **Partitioning**: Segregating data into smaller, manageable segments or partitions.

- **Cleaning**: Removing anomalies, filling in missing values, and eliminating irrelevant or erroneous information.

Preprocessing ensures data integrity and can significantly influence the outcomes of subsequent tasks.

Chunking
********

Vector databases often require data to be in smaller, consistent chunks for efficient storage and retrieval. Chunking involves dividing lengthy texts into smaller segments or chunks, ensuring that each piece retains enough context to be meaningful.

Embeddings
**********

Embeddings convert textual data into fixed-size vectors, preserving semantic context. These vector representations can be used for many tasks, including similarity searches, clustering, and classification. Different embeddings prioritize different aspects of the text, from semantic meaning to sentence structure.

Vector Databases
****************

Vector databases store embeddings in a manner optimized for high-speed similarity searches. Given a query embedding, these databases can quickly retrieve the most similar vectors, facilitating tasks like recommendation, anomaly detection, and clustering.

These foundational concepts provide the groundwork for more advanced NLP methodologies and pipelines. Proper understanding and implementation can vastly improve the outcomes of NLP projects.

Tokens
******

Tokenization decomposes texts into smaller units called tokens. A token might represent a word, part of a word, or even a single character. This process helps analyze and process the text, making it digestible for models and algorithms.

Large Language Models (LLMs)
****************************

LLMs, like GPT, are trained on vast amounts of data and can comprehend and generate human-like text. They have achieved state-of-the-art results across many NLP tasks and can be fine-tuned to cater to specific domains or requirements.

Retrieval Augmented Generation (RAG)
************************************

Large Language Models (LLMs) like OpenAI's ChatGPT and Anthropic's Claude have revolutionized the AI landscape with their prowess. However, they inherently suffer from significant drawbacks. One major issue is their static nature, which means they're "frozen in time." Despite this, LLMs might often respond to newer queries with unwarranted confidence, a phenomenon known as "hallucination."
Such errors can be highly detrimental, mainly when these models serve critical real-world applications.

Retrieval Augmented Generation (RAG) is a groundbreaking technique designed to counteract the limitations of foundational LLMs. By pairing an LLM with an RAG pipeline, we can enable users to access the underlying data sources that the model uses. This transparent approach ensures that an LLM's claims can be verified for accuracy and builds a trust factor among users.

Moreover, RAG offers a cost-effective solution. Instead of bearing the extensive computational and financial burdens of training custom models or fine-tuning existing ones, RAG can, in many situations, serve as a sufficient alternative. This reduction in resource consumption is particularly beneficial for organizations that need more means to develop and deploy foundational models from scratch.

A RAG workflow can be broken down into the following steps:

1. **Data ingestion**: The first step is acquiring data from your relevant sources. We make this easy with our `source connectors <https://unstructured-io.github.io/unstructured/ingest/source_connectors.html>`__.

2. **Data preprocessing and cleaning**: Once you've identified and collected your data sources, removing any unnecessary artifacts within the dataset is a good practice. At Unstructured, we have various tools for data processing in our `core functionalities  <https://unstructured-io.github.io/unstructured/core.html>`__.

3. **Chunking**: The next step is to break your text into digestible pieces for your LLM to consume. We provide the basic and context-aware chunking strategies. Please refer to the documentation `here <https://unstructured-io.github.io/unstructured/core/chunking.html>`__.

4. **Embedding**: After chunking, you must convert the text into a numerical representation (vector embedding) that an LLM can understand. To use the various embedding models using Unstructured tools, please refer to `this page <https://unstructured-io.github.io/unstructured/core/embedding.html>`__.

5. **Vector Database**: The next step is to choose a location for storing your chunked embeddings. There are many options for your vector database (ChromaDB, Milvus, Pinecone, Qdrant, Weaviate, and more). For complete list of Unstructured ``Destination Connectors``, please visit `this page <https://unstructured-io.github.io/unstructured/ingest/destination_connectors.html>`__.

6. **User Prompt**: Take the user prompt and grab the most relevant chunks of information in the vector database via similarity search.

7. **LLM Generation**: Once you've retrieved your relevant chunks, you pass the prompt + the context to the LLM for the LLM to generate a more accurate response.

For a complete guide on how to implement RAG, check out this `blog post <https://medium.com/unstructured-io/effortless-document-extraction-a-guide-to-using-unstructured-api-and-data-connectors-6c2659eda4af>`__
