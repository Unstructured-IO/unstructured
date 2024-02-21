Elasticsearch
======================

Batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem and upload those local files to an Elasticsearch index.

First you'll need to install Elasticsearch dependencies as shown here.

.. code:: shell

  pip install "unstructured[elasticsearch]"

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream local connector.

.. tabs::

   .. tab:: Shell

      .. literalinclude:: ./code/bash/elasticsearch.sh
         :language: bash

   .. tab:: Python

      .. literalinclude:: ./code/python/elasticsearch.py
         :language: python


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> elasticsearch --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.

Vector Search Sample Mapping
----------------------------

To make sure the schema of the index matches the data being written to it, a sample mapping json can be used.

      .. literalinclude:: ./data/elasticsearch_elements_mappings.json
         :language: json
         :linenos:
         :caption: Object description