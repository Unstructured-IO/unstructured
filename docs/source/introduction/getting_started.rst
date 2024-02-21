Quick Start
===========

Installation
------------

This guide offers concise steps to swiftly install and validate your ``unstructured`` installation. For more comprehensive installation guide, please refer to `this page <http://localhost:63342/CHANGELOG.md/docs/build/html/installing.html>`__.

1. **Installing the Python SDK**: 
   You can install the core SDK using pip:
   
   .. code-block:: bash

      pip install unstructured

   Plain text files, HTML, XML, JSON, and Emails are immediately supported without any additional dependencies.

   If you need to process other document types, you can install the extras required by following the :doc:`../installation/full_installation`

2. **System Dependencies**:
   Ensure the subsequent system dependencies are installed. Your requirements might vary based on the document types you're handling:

   - `libmagic-dev` : Essential for filetype detection.
   - `poppler-utils` : Needed for images and PDFs.
   - `tesseract-ocr` : Essential for images and PDFs.
   - `libreoffice` : For MS Office documents.
   - `pandoc` : For EPUBs, RTFs, and Open Office documents.

Validating Installation
-----------------------

After installation, confirm the setup by executing the below Python code:

.. code-block:: python

   from unstructured.partition.auto import partition
   elements = partition(filename="example-docs/eml/fake-email.eml")

If you've opted for the "local-inference" installation, you should also be able to execute:

.. code-block:: python

   from unstructured.partition.auto import partition
   elements = partition("example-docs/layout-parser-paper.pdf")

If these code snippets run without errors, congratulations! Your ``unstructured`` installation is successful and ready for use.


The following section will cover basic concepts and usage patterns in ``unstructured``.
After reading this section, you should be able to:

* Partitioning a document with the ``partition`` function.
* Understand how documents are structured in ``unstructured``.
* Convert a document to a dictionary and/or save it as a JSON.

The example documents in this section come from the
`example-docs <https://github.com/Unstructured-IO/unstructured/tree/main/example-docs>`_
directory in the ``unstructured`` repo.

Before running the code in this make sure you've installed the ``unstructured`` library
and all dependencies using the instructions in the `Quick Start <https://unstructured-io.github.io/unstructured/installing.html#quick-start>`_ section.

Partitioning a document
-----------------------

In this section, we'll cut right to the chase and get to the most important part of the library: partitioning a document.
The goal of document partitioning is to read in a source document, split the document into sections, categorize those sections,
and extract the text associated with those sections. Depending on the document type, unstructured uses different methods for
partitioning a document. We'll cover those in a later section. For now, we'll use the simplest API in the library,
the ``partition`` function. The ``partition`` function will detect the filetype of the source document and route it to the appropriate
partitioning function. You can try out the partition function by running the cell below.

.. code:: python

	from unstructured.partition.auto import partition

	elements = partition(filename="example-10k.html")


You can also pass in a file as a file-like object using the following workflow:

.. code:: python

	with open("example-10k.html", "rb") as f:
	    elements = partition(file=f)


The ``partition`` function uses `libmagic <https://formulae.brew.sh/formula/libmagic>`_ for filetype detection. If ``libmagic`` is
not present and the user passes a filename, ``partition`` falls back to detecting the filetype using the file extension.
``libmagic`` is required if you'd like to pass a file-like object to ``partition``.
We highly recommend installing ``libmagic`` and you may observe different file detection behaviors
if ``libmagic`` is not installed`.


Quickstart Tutorial
-------------------

If you're eager to dive in, head over `Getting Started <https://colab.research.google.com/drive/1U8VCjY2-x8c6y5TYMbSFtQGlQVFHCVIW#scrollTo=jZp37lfueaeZ>`__ on Google Colab to get a hands-on introduction to the ``unstructured`` library. In a few minutes, you'll have a basic workflow set up and running!

For more detailed information about specific components or advanced features, explore the rest of the documentation.
