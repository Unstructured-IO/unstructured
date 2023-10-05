Bricks
======

Bricks are functions that live in ``unstructured`` and are the primary public API for the library.
There are several types of bricks in ``unstructured``, corresponding to the different stages of document pre-processing: partitioning, cleaning, chunking and staging.
After reading this section, you should understand the following:

* How to partition a document into json or csv.
* How to remove unwanted content from document elements using cleaning bricks.
* How to extract content from a document using the extraction bricks.
* How to prepare data for downstream use cases using staging bricks
* How to chunk partitioned documents for use cases such as Retrieval Augmented Generation (RAG).

.. toctree::
   :maxdepth: 1

   bricks/partition
   bricks/cleaning
   bricks/extracting
   bricks/staging
   bricks/chunking
   bricks/embedding
