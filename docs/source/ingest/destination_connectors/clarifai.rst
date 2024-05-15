Clarifai 
===========

Batch process all your records using ``unstructured-ingest`` to store unstructured outputs locally on your filesystem and upload those to Clarifai apps.

First start with the installation of clarifai dependencies as shown here.

.. code:: shell

    pip install "unstructured[clarifai]"

Create a clarifai app with base workflow. Find more information in the `create clarifai app <https://docs.clarifai.com/clarifai-basics/applications/create-an-application/>`_.

Run Locally
-----------
The upstream connector can be any of the ones supported, but for the convenience here, showing a sample command using the upstream local connector.

.. tabs::

    .. tab:: Shell

        .. literatinclude:: ./code/bash/clarifai.sh
            :language: bash
    
    .. tab:: Python

        .. literalinclude:: ./code/python/clarifai.py
            :language: python

For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> clarifai --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.


