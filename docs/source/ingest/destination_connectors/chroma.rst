Chroma
======================

Batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem and upload those to a Chroma database.

First you'll need to install the Chroma dependencies as shown here.

.. code:: shell

  pip install "unstructured[chroma]"

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream local connector.

.. tabs::

   .. tab:: Shell

      .. literalinclude:: ./code/bash/chroma.sh
         :language: bash

   .. tab:: Python

      .. literalinclude:: ./code/python/chroma.py
         :language: python


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> chroma --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.