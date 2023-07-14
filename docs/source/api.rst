Unstructured API
#################

Try our hosted API! It's freely available to use with any of the file types listed above. This is the easiest way to get started, all you need is an API key. You can get your API key `here <https://www.unstructured.io/api-key/>`_ now and start using it today.

Now you can get started with this quick example:

.. code:: shell

	curl -X 'POST' \
	'https://api.unstructured.io/general/v0/general' \
	-H 'accept: application/json' \
	-H 'Content-Type: multipart/form-data' \
	-H 'unstructured-api-key: <YOUR API KEY>' \
	-F 'files=@sample-docs/family-day.eml' \
	| jq -C . | less -R


Below, you will find a more comprehensive overview of the API capabilities. For detailed information on request and response schemas, refer to the `API documentation <https://api.unstructured.io/general/docs#/>`_.

NOTE: You can also host the API locally. For more information check the `Using the API Locally`_ section.


Supported File Types
*********************

========== ========================================================================================================
Category    Output
========== ========================================================================================================
Plaintext   ``.eml``, ``.html``, ``.json``, ``.md``, ``.msg``, ``.rst``, ``.rtf``, ``.txt``, ``.xml``
Images      ``.jpeg``, ``.png``
Documents.  ``.csv``, ``.doc``, ``.docx``, ``.epub``, ``.odt``, ``.pdf``, ``.ppt``, ``.pptx``, ``.tsv``, ``.xlsx``
========== ========================================================================================================

NOTE: Currently, the pipeline is capable of recognizing the file type and choosing the relevant partition function to process the file.


Parameters
***********

Coordinates
============

When elements are extracted from PDFs or images, it may be useful to get their bounding boxes as well. Set the ``coordinates`` parameter to ``true`` to add this field to the elements in the response.

.. code:: shell

  curl -X 'POST' \
  'https://api.unstructured.io/general/v0/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -H 'unstructured-api-key: <YOUR API KEY>' \
  -F 'files=@sample-docs/layout-parser-paper.pdf' \
  -F 'coordinates=true' \
  | jq -C . | less -R


Encoding
=========

You can specify the encoding to use to decode the text input. If no value is provided, ``utf-8`` will be used.

.. code:: shell
	
  curl -X 'POST' \
  'https://api.unstructured.io/general/v0/general' \
  -H 'accept: application/json'  \
  -H 'Content-Type: multipart/form-data' \
  -H 'unstructured-api-key: <YOUR API KEY>' \
  -F 'files=@sample-docs/fake-power-point.pptx' \
  -F 'encoding=utf_8' \
  | jq -C . | less -R


OCR Languages
==============

You can also specify what languages to use for OCR with the ``ocr_languages`` kwarg. See the `Tesseract documentation <https://github.com/tesseract-ocr/tessdata>`_ for a full list of languages and install instructions. OCR is only applied if the text is not already available in the PDF document.

.. code:: shell
	
  curl -X 'POST' \
  'https://api.unstructured.io/general/v0/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -H 'unstructured-api-key: <YOUR API KEY>' \
  -F 'files=@sample-docs/english-and-korean.png' \
  -F 'strategy=ocr_only' \
  -F 'ocr_languages=eng'  \
  -F 'ocr_languages=kor'  \
  | jq -C . | less -R


Output Format
==============

By default the result will be in ``json``, but it can be set to ``text/csv`` to get data in ``csv`` format:

.. code:: shell
	
  curl -X 'POST' \
  'https://api.unstructured.io/general/v0/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -H 'unstructured-api-key: <YOUR API KEY>' \
  -F 'files=@sample-docs/family-day.eml' \
  -F 'output_format="text/csv"'


PDF Table Extraction
=====================

To extract the table structure from PDF files using the ``hi_res`` strategy, ensure that the ``pdf_infer_table_structure`` parameter is set to ``true``. This setting includes the table's text content in the response. By default, this parameter is set to ``false`` to avoid the expensive reading process.

.. code:: shell

  curl -X 'POST' \
  'https://api.unstructured.io/general/v0/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -H 'unstructured-api-key: <YOUR API KEY>' \
  -F 'files=@sample-docs/layout-parser-paper.pdf' \
  -F 'strategy=hi_res' \
  -F 'pdf_infer_table_structure=true' \
  | jq -C . | less -R


Strategies
===========

Four strategies are available for processing PDF/Images files: ``hi_res``, ``fast``, ``ocr_only``, and ``auto``. ``fast`` is the default ``strategy`` and works well for documents that do not have text embedded in images.

On the other hand, ``hi_res`` is the better choice for PDFs that may have text within embedded images, or for achieving greater precision of `element types <https://unstructured-io.github.io/unstructured/getting_started.html#document-elements>`_ in the response JSON. Be aware that ``hi_res`` requests may take 20 times longer to process compared to the ``fast`` option. See the example below for making a ``hi_res`` request.

.. code:: shell
	
  curl -X 'POST' \
  'https://api.unstructured.io/general/v0/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -H 'unstructured-api-key: <YOUR API KEY>' \
  -F 'files=@sample-docs/layout-parser-paper.pdf' \
  -F 'strategy=hi_res' \
  | jq -C . | less -R

The ``ocr_only`` strategy runs the document through Tesseract for OCR. Currently, ``hi_res`` has difficulty ordering elements for documents with multiple columns. If you have a document with multiple columns that do not have extractable text, it's recommended that you use the ``ocr_only`` strategy. Please be aware that ``ocr_only`` will fall back to another strategy if Tesseract is not available.

For the best of all worlds, ``auto`` will determine when a page can be extracted using ``fast`` or ``ocr_only`` mode, otherwise, it will fall back to hi_res.


XML Tags
=========

When processing XML documents, set the ``xml_keep_tags`` parameter to ``true`` to retain the XML tags in the output. If not specified, it will simply extract the text from within the tags.

.. code:: shell
	
  curl -X 'POST' \
  'https://api.unstructured.io/general/v0/general' \
  -H 'accept: application/json'  \
  -H 'Content-Type: multipart/form-data' \
  -H 'unstructured-api-key: <YOUR API KEY>' \
  -F 'files=@sample-docs/fake-xml.xml' \
  -F 'xml_keep_tags=true' \
  | jq -C . | less -R


Using the API Locally
**********************

If you are self-hosting the API or running it locally, it's strongly suggested that you do so running the Docker container.

Using Docker Images
====================

The following instructions are intended to help you get up and running using Docker to interact with ``unstructured-api``. See `here <https://docs.docker.com/get-docker/>`_ if you don't already have docker installed on your machine.

NOTE: Multi-platform images are built to support both x86_64 and Apple silicon hardware. Docker pull should download the corresponding image for your architecture, but you can specify with ``--platform`` (e.g. ``--platform linux/amd64``) if needed.

Docker images is built for all pushes to ``main``. Each image is tagged with the corresponding short commit hash (e.g. ``fbc7a69``) and the application version (e.g. ``0.5.5-dev1``). Also, the most recent image is tagged with ``latest``. To leverage this, use ``docker pull`` from the image repository.

.. code:: shell
	
  docker pull quay.io/unstructured-io/unstructured-api:latest

Once pulled, you can launch the container as a web app on localhost:8000.

.. code:: shell
	
  docker run -p 8000:8000 -d --rm --name unstructured-api quay.io/unstructured-io/unstructured-api:latest --port 8000 --host 0.0.0.0


Developing with the API Locally
================================

To get started you'll need to fork the ``unstructured-api`` repository `here <https://github.com/Unstructured-IO/unstructured-api>`_.

* Run ``make install``
* Sart one of the following:
	- A local jupyter notebook server with ``make run-jupyter``
	- The fast-API with ``make run-web-app``

NOTE: See the `Unstructured Installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_ for the many OS dependencies that are required, if the ability to process all file types is desired.

You can now hit the API locally at port 8000. The ``sample-docs`` directory has several example file types that are currently supported.

For example:

.. code:: shell
	
  curl -X 'POST' \
  'http://localhost:8000/general/v0/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@sample-docs/family-day.eml' \
  | jq -C . | less -R