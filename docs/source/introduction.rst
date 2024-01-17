Introduction
============

Product Offerings
*****************

Unstructured API Services
-------------------------

- **Unstructured SaaS API**: A scalable, highly-optimized API service hosted on Unstructured's infrastructure. Learn more and access the API here: `SaaS API <https://unstructured-io.github.io/unstructured/apis/saas_api.html>`__.

- **Azure and AWS Marketplace APIs**: Enables deployment of the Unstructured API on cloud infrastructure. Access via `Azure Marketplace <https://unstructured-io.github.io/unstructured/apis/azure_marketplace.html>`__ or `AWS Marketplace <https://unstructured-io.github.io/unstructured/apis/aws_marketplace.html>`__.

Enterprise Platform
-------------------

- **Enterprise Platform**: Scheduled for launch in early 2024, this platform is designed to offer comprehensive enterprise-grade support and solutions.

Open Source Solutions
---------------------

- **Unstructured Core Library**: The open-source library offering core functionalities of Unstructured. Access it at the `unstructured GitHub repository <https://github.com/Unstructured-IO/unstructured>`__.

- **Model Inference for Layout Parsing**: Specialized in model inference for layout parsing tasks. Explore this at the `unstructured-inference GitHub repository <https://github.com/Unstructured-IO/unstructured-inference>`__.

- **Self Hosting API**: Offers an API for self-hosting purposes. More details can be found at the `unstructured-api GitHub repository <https://github.com/Unstructured-IO/unstructured-api>`__.


Key Features
************

- **Precise Document Extraction**: Unstructured offers advanced capabilities in extracting elements and metadata from documents. This includes a variety of document element types and metadata. Learn more about `Document Elements <https://unstructured-io.github.io/unstructured/introduction/getting_started.html#elements>`__ and `Metadata <https://unstructured-io.github.io/unstructured/metadata.html>`__.

- **Extensive File Support**: The platform supports a wide array of file types, ensuring versatility in handling different document formats from PDF, Images, HTML, and many more. Detailed information on supported file types can be found `here <https://unstructured-io.github.io/unstructured/api.html#supported-file-types>`__.

- **Robust Core Functionality**: Unstructured provides a suite of core functionalities critical for efficient data processing. This includes:

  * `Partitioning <https://unstructured-io.github.io/unstructured/core/partition.html>`__: The partitioning functions in Unstructured enable the extraction of structured content from raw, unstructured documents. This feature is crucial for transforming unorganized data into usable formats, aiding in efficient data processing and analysis.
  * `Cleaning <https://unstructured-io.github.io/unstructured/core/cleaning.html>`__: Data preparation for NLP models often requires cleaning to ensure quality. The Unstructured library includes cleaning functions that assist in sanitizing output, removing unwanted content, and improving the performance of NLP models. This step is essential for maintaining the integrity of data before it is passed to downstream applications.
  * `Extracting <https://unstructured-io.github.io/unstructured/core/extracting.html>`__: This functionality allows for the extraction of specific entities within documents. It is designed to identify and isolate relevant pieces of information, making it easier for users to focus on the most pertinent data in their documents.
  * `Staging <http://localhost:63342/CHANGELOG.md/docs/build/html/core/staging.html>`__: Staging functions help prepare your data for ingestion into downstream systems. Please note that this functionality is being deprecated in favor of ``Destination Connectors``.
  * `Chunking <https://unstructured-io.github.io/unstructured/core/chunking.html>`__: The chunking process in Unstructured is distinct from conventional methods. Instead of relying solely on text-based features to form chunks, Unstructured uses a deep understanding of document formats to partition documents into semantic units (document elements).
  * `Embedding <https://unstructured-io.github.io/unstructured/core/chunking.html>`__: The embedding encoder classes in Unstructured leverage document elements detected through partitioning or grouped via chunking to obtain embeddings for each element. This is particularly useful for applications like Retrieval Augmented Generation (RAG), where precise and contextually relevant embeddings are crucial.

- **High-performant Connectors**: The platform includes optimized connectors for efficient data ingestion and output. These comprise `Source Connectors <https://unstructured-io.github.io/unstructured/ingest/source_connectors.html>`__ for data input and `Destination Connectors <https://unstructured-io.github.io/unstructured/ingest/destination_connectors.html>`__ for data export.

Common Use Cases
****************

- Pretraining Models
- Fine-tuning Models
- Retrieval Augmented Generation (RAG)
- Traditional ETL


.. toctree::
   :maxdepth: 1
   :hidden:

   introduction/getting_started
   introduction/overview
   introduction/key_concepts
