Core Functionality
==================

The ``unstructured`` library includes functions to partition, chunk, clean, and stage
raw source documents. These functions serve as the primary public interfaces within the library.
After reading this section, you should understand the following:

* How to partition a document into json or csv.
* How to remove unwanted content from document elements using cleaning functions.
* How to extract content from a document using the extraction functions.
* How to prepare data for downstream use cases using staging functions
* How to chunk partitioned documents for use cases such as Retrieval Augmented Generation (RAG).

.. toctree::
   :maxdepth: 1

   core/partition
   core/cleaning
   core/extracting
   core/staging
   core/chunking
   core/embedding
