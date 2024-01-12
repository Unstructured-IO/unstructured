SQL
===========
NOTE: At the moment, the connector only supports PostgreSQL and SQLite. Vectors can be stored and searched in PostgreSQL with pgvector.

Batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem and upload those local files to a PostgreSQL or SQLite schema.

Insert query is currently limited to append.

First you'll need to install the sql dependencies as shown here if you are using PostgreSQL.

.. code:: shell

  pip install "unstructured[postgres]"

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream local connector.

.. tabs::

   .. tab:: Shell

      .. literalinclude:: ./code/bash/sql.sh
         :language: bash

   .. tab:: Python

      .. literalinclude:: ./code/python/sql.py
         :language: python

For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> sql --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.

Sample Index Schema
-------------------

To make sure the schema of the index matches the data being written to it, a sample schema json can be used.

.. tabs::

   .. tab:: PostgreSQL
      .. literalinclude:: ./data/postgres-schema.sql
         :language: sql
         :linenos:
         :caption: Object description

   .. tab:: PostgreSQL with pgvector

      .. literalinclude:: ./data/pgvector-schema.sql
         :language: sql
         :linenos:
         :caption: Object description

   .. tab:: Sqlite

      .. literalinclude:: ./data/sqlite-schema.sql
         :language: sql
         :linenos:
         :caption: Object description