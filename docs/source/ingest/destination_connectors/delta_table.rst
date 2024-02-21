Delta Table
===========

Batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem and upload those local files to a Delta Table.

First you'll need to install the delta table dependencies as shown here.

.. code:: shell

  pip install "unstructured[delta-table]"

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream local connector.

.. tabs::

   .. tab:: Shell

      .. literalinclude:: ./code/bash/delta_table.sh
         :language: bash

   .. tab:: Python

      .. literalinclude:: ./code/python/delta_table.py
         :language: python


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> delta-table --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
