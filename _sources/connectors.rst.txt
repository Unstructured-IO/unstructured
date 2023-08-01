Connectors
==========
Connect your preprocessing pipeline with your favorite data storage platforms, and batch process all your documents using the provided CLI to store structured outputs locally on your filesystem. 

You can then use any connector with the ``unstructured-ingest`` command in the terminal. For example, the following command processes all the documents in S3 in the utic-dev-tech-fixtures bucket with a prefix of small-pdf-set/

.. code:: shell

  unstructured-ingest \
    --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
    --s3-anonymous \
    --structured-output-dir s3-small-batch-output \
    --num-processes 2

To run this example, you'll first need to install the S3 dependencies as shown `here <https://unstructured-io.github.io/unstructured/connectors.html#s3-connector>`_.

For a full list of the options the CLI accepts check ``unstructured-ingest --help``.

You can also use connectors with the ``unstructured`` API. For this you'll need to use the ``--partition-by-api`` flag and pass in your API key with ``--api-key``. Additionaly, you will need to pass the ``--partition-endpoint`` if you're running the API locally. You can find more information about the ``unstructured`` API `here <https://github.com/Unstructured-IO/unstructured-api>`_.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.


``Azure Connector``
--------------------
You can batch process documents stored in your Azure Blob Container using the `Azure Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/azure.py>`_. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/azure/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[azure]``


``BioMed Connector``
---------------------
You can process `National Center for Biotechnology Information <https://www.ncbi.nlm.nih.gov/>`_ files from both a path or their `PMC API <https://www.ncbi.nlm.nih.gov/pmc/tools/developers/>`_ through the `BioMed Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/biomed.py>`_. You can find an example of how to use it with the file path `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/biomed/ingest-with-path.sh>`_, and with the API `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/biomed/ingest-with-api.sh>`_.


``Discord Connector``
----------------------
You can preprocess your Discord channel using the `Discord Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/discord.py>`_. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/discord/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[discord]``


``Dropbox Connector``
----------------------
You can batch process unstructured documents in your Dropbox by using the `Dropbox Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/dropbox.py>`_. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/dropbox/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[dropbox]``


``Elasticsearch Connector``
----------------------------
You can preprocess documents stored in Elasticsearch by using the `Elasticsearch Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/elasticsearch.py>`_. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/elasticsearch/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[elasticsearch]``


``Google Cloud Storage Connector``
------------------
You can batch load the files you have stored in Google Cloud Storage with the `GCS Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/gcs.py>`_. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/google_cloud_storage/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[gcs]``


``Github Connector``
---------------------
You can process files in a Github repository using the `Github Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/github.py>`_. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/github/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[github]``


``Gitlab Connector``
---------------------
You can batch load files in a Gitlab repository using the `Gitlab Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/gitlab.py>`_. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/gitlab/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[gitlab]``


``Google Drive Connector``
---------------------
You can batch process documents stored in your Google Drive with the `Google Drive Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/google_drive.py>`_. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/google_drive/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[google-drive]``


``Local Connector``
---------------------
You can batch load your unstructured files in a local directory for preprocessing using the `Local Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/local.py>`_. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/local/ingest.sh>`_.


``Reddit Connector``
---------------------
You can use the `Reddit Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/reddit.py>`_ to preprocess a Reddit thread. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/reddit/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[reddit]``


``S3 Connector``
---------------------
You can process your files stored in S3 in batch using the `S3 Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/s3.py>`_. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/s3-small-batch/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[s3]``


``Slack Connector``
---------------------
Using the `Slack Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/slack.py>`_ you can batch process a channel. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/slack/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[slack]``


``Wikipedia Connector``
---------------------
You can load and process a Wikipedia page using the `Wikipedia Connector <https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/ingest/connector/slack.py>`_ to preprocess for your model. You can find an example of how to use it `here <https://github.com/Unstructured-IO/unstructured/blob/f5541c7b0b1e2fc47ec88da5e02080d60e1441e2/examples/ingest/wikipedia/ingest.sh>`_.

To install all dependencies for this connector run: ``pip install unstructured[wikipedia]``
