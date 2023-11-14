Unstructured API
#################

Try our hosted API! It's freely available to use with any of the file types listed above. This is the easiest way to get started, all you need is an API key. You can get your API key `here <https://unstructured.io/#get-api-key>`__ now and start using it today.

Now you can get started with this quick example:

.. tabs::

   .. tab:: Shell

      .. code:: shell

         curl -X 'POST' \
         'https://api.unstructured.io/general/v0/general' \
         -H 'accept: application/json' \
         -H 'Content-Type: multipart/form-data' \
         -H 'unstructured-api-key: <YOUR API KEY>' \
         -F 'files=@sample-docs/family-day.eml' \
         | jq -C . | less -R

   .. tab:: Python

      .. code:: python

        import requests

        url = 'https://api.unstructured.io/general/v0/general'

        headers = {
            'accept': 'application/json',
            'unstructured-api-key': '<API-KEY>',
        }

        data = {
            'strategy': 'auto',
        }

        file_path = "/Path/To/File"
        file_data = {'files': open(file_path, 'rb')}

        response = requests.post(url, headers=headers, data=data, files=file_data)

        file_data['files'].close()

        json_response = response.json()

Below, you will find a more comprehensive overview of the API capabilities. For detailed information on request and response schemas, refer to the `API documentation <https://api.unstructured.io/general/docs#/>`__.

NOTE: You can also host the API locally. For more information check the `Using the API Locally <https://github.com/Unstructured-IO/unstructured-api>`__ section.


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

.. tabs::

  .. tab:: Shell

    .. code:: shell

      curl -X 'POST' \
      'https://api.unstructured.io/general/v0/general' \
      -H 'accept: application/json' \
      -H 'Content-Type: multipart/form-data' \
      -H 'unstructured-api-key: <YOUR API KEY>' \
      -F 'files=@example-docs/layout-parser-paper.pdf' \
      -F 'coordinates=true' \
      | jq -C . | less -R
    
  .. tab:: Python
    
    .. code:: python

      import requests

      url = "https://api.unstructured.io/general/v0/general"

      headers = {
          "accept": "application/json",
          "Content-Type": "multipart/form-data",
          "unstructured-api-key": "<YOUR API KEY>"
      }

      data = {
          "coordinates": "true"
      }

      file_path = "/Path/To/File"
      file_data = {'files': open(file_path, 'rb')}

      response = requests.post(url, headers=headers, files=file_data, data=data)
      
      file_data['files'].close()

      json_response = response.json()

Encoding
=========

You can specify the encoding to use to decode the text input. If no value is provided, ``utf-8`` will be used.

.. tabs::

  .. tab:: Shell

    .. code:: shell

      curl -X 'POST' \
      'https://api.unstructured.io/general/v0/general' \
      -H 'accept: application/json'  \
      -H 'Content-Type: multipart/form-data' \
      -H 'unstructured-api-key: <YOUR API KEY>' \
      -F 'files=@example-docs/fake-power-point.pptx' \
      -F 'encoding=utf_8' \
      | jq -C . | less -R

  .. tab:: Python

    .. code:: python

      import requests

      url = "https://api.unstructured.io/general/v0/general"

      headers = {
          "accept": "application/json",
          "Content-Type": "multipart/form-data",
          "unstructured-api-key": "<YOUR API KEY>"
      }

      data = {
          "encoding": "utf_8"
      }

      file_path = "/Path/To/File"
      file_data = {'files': open(file_path, 'rb')}

      response = requests.post(url, headers=headers, files=file_data, data=data)

      file_data['files'].close()

      json_response = response.json()

OCR Languages
==============

You can also specify what languages to use for OCR with the ``ocr_languages`` kwarg. See the `Tesseract documentation <https://github.com/tesseract-ocr/tessdata>`_ for a full list of languages and install instructions. OCR is only applied if the text is not already available in the PDF document.

.. tabs::

  .. tab:: Shell

    .. code:: shell

      curl -X 'POST' \
      'https://api.unstructured.io/general/v0/general' \
      -H 'accept: application/json' \
      -H 'Content-Type: multipart/form-data' \
      -H 'unstructured-api-key: <YOUR API KEY>' \
      -F 'files=@example-docs/english-and-korean.png' \
      -F 'strategy=ocr_only' \
      -F 'ocr_languages=eng'  \
      -F 'ocr_languages=kor'  \
      | jq -C . | less -R

  .. tab:: Python

    .. code:: python

      import requests

      url = "https://api.unstructured.io/general/v0/general"

      headers = {
          "accept": "application/json",
          "unstructured-api-key": "<YOUR API KEY>"
      }

      data = {
          "strategy": "ocr_only",
          "ocr_languages": ["eng", "kor"]
      }

      file_path = "/Path/To/File"
      file_data = {'files': open(file_path, 'rb')}

      response = requests.post(url, headers=headers, files=file_data, data=data)

      file_data['files'].close()

      json_response = response.json()

Output Format
==============

By default the result will be in ``json``, but it can be set to ``text/csv`` to get data in ``csv`` format:

.. tabs:: 

  .. tab:: Shell

    .. code:: shell

      curl -X 'POST' \
      'https://api.unstructured.io/general/v0/general' \
      -H 'accept: application/json' \
      -H 'Content-Type: multipart/form-data' \
      -H 'unstructured-api-key: <YOUR API KEY>' \
      -F 'files=@example-docs/family-day.eml' \
      -F 'output_format="text/csv"'

  .. tab:: Python

    .. code:: python

      import requests

      url = "https://api.unstructured.io/general/v0/general"

      headers = {
          "accept": "application/json",
          "unstructured-api-key": "<YOUR API KEY>"
      }

      data = {
          "strategy": "ocr_only",
          "ocr_languages": ["eng", "kor"]
      }

      file_path = "/Path/To/File"
      file_data = {'files': open(file_path, 'rb')}

      response = requests.post(url, headers=headers, files=file_data, data=data)

      file_data['files'].close()

      json_response = response.json()

Page Break
===========

Pass the `include_page_breaks` parameter to `true` to include `PageBreak` elements in the output.

.. tabs::

  .. tab:: Shell

    .. code:: shell

      curl -X 'POST' \
      'https://api.unstructured.io/general/v0/general' \
      -H 'accept: application/json' \
      -H 'Content-Type: multipart/form-data' \
      -H 'unstructured-api-key: <YOUR API KEY>' \
      -F 'files=@example-docs/family-day.eml' \
      -F 'include_page_breaks=true' \
      | jq -C . | less -R

  .. tab:: Python

    .. code:: python

      import requests

      url = "https://api.unstructured.io/general/v0/general"

      headers = {
          "accept": "application/json",
          "unstructured-api-key": "<YOUR API KEY>"
      }

      data = {
          "include_page_breaks": "true"
      }

      file_path = "/Path/To/File"
      file_data = {'files': open(file_path, 'rb')}

      response = requests.post(url, headers=headers, files=file_data, data=data)

      file_data['files'].close()

      json_response = response.json()


Strategies
===========

Four strategies are available for processing PDF/Images files: ``hi_res``, ``fast``, ``ocr_only``, and ``auto``. ``fast`` is the default ``strategy`` and works well for documents that do not have text embedded in images.

On the other hand, ``hi_res`` is the better choice for PDFs that may have text within embedded images, or for achieving greater precision of `element types <https://unstructured-io.github.io/unstructured/getting_started.html#document-elements>`_ in the response JSON. Be aware that ``hi_res`` requests may take 20 times longer to process compared to the ``fast`` option. See the example below for making a ``hi_res`` request.

.. tabs::

  .. tab:: Shell

    .. code:: shell

      curl -X 'POST' \
      'https://api.unstructured.io/general/v0/general' \
      -H 'accept: application/json' \
      -H 'Content-Type: multipart/form-data' \
      -H 'unstructured-api-key: <YOUR API KEY>' \
      -F 'files=@example-docs/layout-parser-paper.pdf' \
      -F 'strategy=hi_res' \
      | jq -C . | less -R

  .. tab:: Python

    .. code:: python

      import requests

      url = "https://api.unstructured.io/general/v0/general"

      headers = {
          "accept": "application/json",
          "unstructured-api-key": "<YOUR API KEY>"
      }

      data = {
          "strategy": "hi_res"
      }

      file_path = "/Path/To/File"
      file_data = {'files': open(file_path, 'rb')}

      response = requests.post(url, headers=headers, files=file_data, data=data)

      file_data['files'].close()

      json_response = response.json()

The ``ocr_only`` strategy runs the document through Tesseract for OCR. Currently, ``hi_res`` has difficulty ordering elements for documents with multiple columns. If you have a document with multiple columns that do not have extractable text, it's recommended that you use the ``ocr_only`` strategy. Please be aware that ``ocr_only`` will fall back to another strategy if Tesseract is not available.

For the best of all worlds, ``auto`` will determine when a page can be extracted using ``fast`` or ``ocr_only`` mode, otherwise, it will fall back to hi_res.

Beta Version: ``hi_res`` Strategy with Chipper Model
-----------------------------------------------------

To use the ``hi_res`` strategy with **Chipper** model, pass the argument for ``hi_res_model_name`` as shown in the code block below.

.. tabs::

  .. tab:: Shell

    .. code:: shell

        curl -X 'POST' \
          'https://api.unstructured.io/general/v0/general' \
          -H 'accept: application/json' \
          -H 'Content-Type: multipart/form-data' \
          -H 'unstructured-api-key: <YOUR API KEY>' \
          -F 'strategy=hi_res' \
          -F 'hi_res_model_name=chipper' \
          -F 'files=@example-docs/layout-parser-paper-fast.pdf' \
          -F 'strategy=hi_res' \
          | jq -C . | less -R

  .. tab:: Python

    .. code:: python

      import requests

      url = "https://api.unstructured.io/general/v0/general"

      headers = {
          "accept": "application/json",
          "unstructured-api-key": "<YOUR API KEY>"
      }

      data = {
          "strategy": "hi_res",
          "hi_res_model_name": "chipper"
      }

      file_path = "/Path/To/File"
      file_data = {'files': open(file_path, 'rb')}

      response = requests.post(url, headers=headers, files=file_data, data=data)

      file_data['files'].close()

      json_response = response.json()

*Please note that the Chipper model does not currently support the coordinates argument.*

Table Extraction
=====================

PDF Table Extraction
---------------------

To extract the table structure from PDF files using the ``hi_res`` strategy, ensure that the ``pdf_infer_table_structure`` parameter is set to ``true``. This setting includes the table's text content in the response. By default, this parameter is set to ``false`` because table extraction is computationally expensive.

.. tabs::

  .. tab:: Shell

    .. code:: shell

      curl -X 'POST' \
      'https://api.unstructured.io/general/v0/general' \
      -H 'accept: application/json' \
      -H 'Content-Type: multipart/form-data' \
      -H 'unstructured-api-key: <YOUR API KEY>' \
      -F 'files=@example-docs/layout-parser-paper.pdf' \
      -F 'strategy=hi_res' \
      -F 'pdf_infer_table_structure=true' \
      | jq -C . | less -R

  .. tab:: Python

    .. code:: python

      import requests

      url = "https://api.unstructured.io/general/v0/general"

      headers = {
          "accept": "application/json",
          "unstructured-api-key": "<YOUR API KEY>"
      }

      data = {
          "strategy": "hi_res",
          "pdf_infer_table_structure": "true"
      }

      file_path = "/Path/To/File"
      file_data = {'files': open(file_path, 'rb')}

      response = requests.post(url, headers=headers, files=file_data, data=data)

      file_data['files'].close()

      json_response = response.json()

Table Extraction for other filetypes
------------------------------------

We also provide support for enabling and disabling table extraction for file types other than PDF files. Set parameter ``skip_infer_table_types`` to specify the document types that you want to skip table extraction with. By default, we skip table extraction for PDFs, Images, and Excel files which are ``pdf``, ``jpg``, ``png``, ``xlsx``, and ``xls``. Note that table extraction for Images and PDFs only works with ``hi_res`` strategy. For example, if you don't want to skip table extraction for images, you can pass an empty value to ``skip_infer_table_types`` with:

.. tabs::

  .. tab:: Shell

    .. code:: shell

      curl -X 'POST' \
      'https://api.unstructured.io/general/v0/general' \
      -H 'accept: application/json' \
      -H 'Content-Type: multipart/form-data' \
      -H 'unstructured-api-key: <YOUR API KEY>' \
      -F 'files=@example-docs/layout-parser-paper-with-table.jpg' \
      -F 'strategy=hi_res' \
      -F 'skip_infer_table_types=[]' \
      | jq -C . | less -R

  .. tab:: Python

    .. code:: python

      import requests

      url = "https://api.unstructured.io/general/v0/general"

      headers = {
          "accept": "application/json",
          "unstructured-api-key": "<YOUR API KEY>"
      }

      data = {
          "strategy": "hi_res",
          "skip_infer_table_types": "[]"
      }

      file_path = "/Path/To/File"
      file_data = {'files': open(file_path, 'rb')}

      response = requests.post(url, headers=headers, files=file_data, data=data)

      file_data['files'].close()

      json_response = response.json()

XML Tags
=========

When processing XML documents, set the ``xml_keep_tags`` parameter to ``true`` to retain the XML tags in the output. If not specified, it will simply extract the text from within the tags.

.. tabs::

  .. tab:: Shell

    .. code:: shell

      curl -X 'POST' \
      'https://api.unstructured.io/general/v0/general' \
      -H 'accept: application/json'  \
      -H 'Content-Type: multipart/form-data' \
      -H 'unstructured-api-key: <YOUR API KEY>' \
      -F 'files=@example-docs/fake-xml.xml' \
      -F 'xml_keep_tags=true' \
      | jq -C . | less -R

  .. tab:: Python

    .. code:: python

      import requests

      url = "https://api.unstructured.io/general/v0/general"

      headers = {
          "accept": "application/json",
          "unstructured-api-key": "<YOUR API KEY>"
      }

      data = {
          "xml_keep_tags": "true"
      }

      file_path = "/Path/To/File"
      file_data = {'files': open(file_path, 'rb')}

      response = requests.post(url, headers=headers, files=file_data, data=data)

      file_data['files'].close()

      json_response = response.json()     


Using the API Locally
**********************

If you are self-hosting the API or running it locally, it's strongly suggested that you do so running the Docker container.

Using Docker Images
====================

The following instructions are intended to help you get up and running using Docker to interact with ``unstructured-api``. See `docker <https://docs.docker.com/get-docker/>`_ if you don't already have docker installed on your machine.

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

You can now hit the API locally at port 8000. The ``example-docs`` directory has several example file types that are currently supported.

For example:

.. code:: shell

  curl -X 'POST' \
  'http://localhost:8000/general/v0/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@example-docs/family-day.eml' \
  | jq -C . | less -R
