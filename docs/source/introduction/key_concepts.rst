Key Concepts
============

Natural Language Processing (NLP) encompasses a broad spectrum of tasks and methodologies. This section introduces some fundamental concepts crucial for most NLP projects that involve Unstructured's products.

Data Ingestion
**************

Unstructured's ``Source Connectors`` make data ingestion easy. They ensure that your data is accessible, up to date, and usable for any downstream task. If you'd like to read more on our upstream connectors, you can find details `here <https://unstructured-io.github.io/unstructured/ingest/source_connectors.html>`__.

Data Preprocessing
******************

Before the core analysis, raw data often requires significant preprocessing:

- **Partitioning**: Segregating data into smaller, manageable segments or partitions.

- **Cleaning**: Removing anomalies, filling missing values, and eliminating any irrelevant or erroneous information.

Preprocessing ensures data integrity and can significantly influence the outcomes of subsequent tasks.

Chunking
********

Vector databases often require data to be in smaller, consistent chunks for efficient storage and retrieval. Chunking involves dividing lengthy texts into smaller segments or chunks, ensuring that each piece retains enough context to be meaningful.

Embeddings
**********

Embeddings convert textual data into fixed-size vectors, preserving semantic context. These vector representations can then be used for a myriad of tasks, including similarity searches, clustering, and classification. Different embeddings might prioritize different aspects of the text, from semantic meaning to sentence structure.

Vector Databases
****************

Vector databases store embeddings in a manner optimized for high-speed similarity searches. Given a query embedding, these databases can quickly retrieve the most similar vectors, facilitating tasks like recommendation, anomaly detection, and clustering.

These foundational concepts provide the groundwork for more advanced NLP methodologies and pipelines. Proper understanding and implementation can vastly improve the outcomes of NLP projects.

Tokens
******

Tokenization decomposes texts into smaller units, called tokens. A token might represent a word, part of a word, or even a single character. This process helps in analyzing and processing the text, making it digestible for models and algorithms.

Large Language Models (LLMs)
****************************

LLMs, like GPT, are trained on vast amounts of data and have the capacity to comprehend and generate human-like text. They have achieved state-of-the-art results across a multitude of NLP tasks and can be fine-tuned to cater to specific domains or requirements.

Retrieval Augmented Generation (RAG)
************************************

Large Language Models (LLMs) like OpenAI's ChatGPT and Anthropic's Claude have revolutionized the AI landscape with their prowess. However, they inherently suffer from significant drawbacks. One major issue is their static nature, which means they're "frozen in time".
For instance, ChatGPT's knowledge is limited up to September 2021, leaving it blind to any developments or information post that period. Despite this, LLMs might often respond to newer queries with unwarranted confidence, a phenomenon known as "hallucination".
Such errors can be highly detrimental, especially when these models serve critical real-world applications.

Retrieval Augmented Generation (RAG) is a groundbreaking technique designed to counteract the limitations of foundational LLMs. By pairing an LLM with a RAG pipeline, we can enable users to access the underlying data sources that the model uses. This transparent approach not
only ensures that an LLM's claims can be verified for accuracy but also builds a trust factor among users.

Moreover, RAG offers a cost-effective solution. Instead of bearing the extensive computational and financial burdens of training custom models or finetuning existing ones, RAG can, in many situations, serve as a sufficient alternative. This reduction in resource consumption
is particularly beneficial for organizations that lack the means to develop and deploy foundational models from scratch.

A RAG workflow can be broken down into the following steps:

1. **Data ingestion**: The first step is acquiring data from your relevant sources. At Unstructured we make this super easy with our `data connectors <https://unstructured-io.github.io/unstructured/source_connectors.html>`__.

2. **Data preprocessing and cleaning**: Once you've identified and collected your data sources a good practice is to remove any unnecessary artifacts within the dataset. At Unstructured we have a variety of different tools to remove unneccesary elements. Found `here <https://unstructured-io.github.io/unstructured/functions.html>`_

3. **Chunking**: The next step is to break your text down into digestable pieces for your LLM to be able to consume. LangChain, Llama Index and Haystack offer chunking funcionalities.

4. **Embedding**: After chunking, you will need to convert the text into a numerical representation (vector embedding) that a LLM can understand. OpenAI, Cohere, and Hugging Face all offer embedding models.

5. **Vector Database**: The next step is to choose a location for storing your chunked embeddings. There are lots of options to choose from for your vector database (ChromaDB, Milvus, Pinecone, Qdrant, Weaviate and more).

6. **User Prompt**: Take the user prompt and grab the most relevant chunks of information in the vector database via similarity search.

7. **LLM Generation**: Once you've retrieved your relevant chunks you pass the prompt + the context to the LLM for the LLM to generate a more accurate response.

For a full guide on how to implement RAG check out this `blog post <https://medium.com/unstructured-io/effortless-document-extraction-a-guide-to-using-unstructured-api-and-data-connectors-6c2659eda4af>`__
