Delta Table
===========

Connect delta tables to your preprocessing pipeline, and batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem.

First you'll need to install the delta table dependencies as shown here.

.. code:: shell

  pip install "unstructured[delta-table]"

Run Locally
-----------

.. tabs::

   .. tab:: Shell

      .. literalinclude:: ./code/bash/delta_table.sh
         :language: bash

   .. tab:: Python

      .. literalinclude:: ./code/python/delta_table.py
         :language: python


Run via the API
---------------

You can also use upstream connectors with the ``unstructured`` API. For this you'll need to use the ``--partition-by-api`` flag and pass in your API key with ``--api-key``.

.. tabs::

   .. tab:: Shell

      .. literalinclude:: ./code/bash/delta_table_api.sh
         :language: bash

   .. tab:: Python

      .. literalinclude:: ./code/python/delta_table_api.py
         :language: python

Additionally, you will need to pass the ``--partition-endpoint`` if you're running the API locally. You can find more information about the ``unstructured`` API `here <https://github.com/Unstructured-IO/unstructured-api>`_.

For a full list of the options the CLI accepts check ``unstructured-ingest delta-table --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
