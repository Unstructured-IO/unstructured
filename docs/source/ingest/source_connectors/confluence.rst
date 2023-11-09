Confluence
==========
Connect Confluence to your preprocessing pipeline, and batch process all your documents using ``unstructured-ingest`` to store structured outputs locally on your filesystem.

First you'll need to install the Confluence dependencies as shown here.

.. code:: shell

  pip install "unstructured[confluence]"

Run Locally
-----------

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
          confluence \
          --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
          --url https://unstructured-ingest-test.atlassian.net \
          --user-email 12345678@unstructured.io \
          --api-token ABCDE1234ABDE1234ABCDE1234 \
          --output-dir confluence-ingest-output \
          --num-processes 2

   .. tab:: Python

      .. code:: python

        import os

        from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
        from unstructured.ingest.runner import ConfluenceRunner

        if __name__ == "__main__":
            runner = ConfluenceRunner(
                processor_config=ProcessorConfig(
                    verbose=True,
                    output_dir="confluence-ingest-output",
                    num_processes=2,
                ),
                read_config=ReadConfig(),
                partition_config=PartitionConfig(
                    metadata_exclude=["filename", "file_directory", "metadata.data_source.date_processed"],
                ),
            )
            runner.run(
                url="https://unstructured-ingest-test.atlassian.net",
                user_email="12345678@unstructured.io",
                api_token="ABCDE1234ABDE1234ABCDE1234",
            )

Run via the API
---------------

You can also use upstream connectors with the ``unstructured`` API. For this you'll need to use the ``--partition-by-api`` flag and pass in your API key with ``--api-key``.

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
          confluence \
          --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
          --url https://unstructured-ingest-test.atlassian.net \
          --user-email 12345678@unstructured.io \
          --api-token ABCDE1234ABDE1234ABCDE1234 \
          --output-dir confluence-ingest-output \
          --num-processes 2 \
          --partition-by-api \
          --api-key "<UNSTRUCTURED-API-KEY>"

   .. tab:: Python

      .. code:: python

        import os

        from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
        from unstructured.ingest.runner import ConfluenceRunner

        if __name__ == "__main__":
            runner = ConfluenceRunner(
                processor_config=ProcessorConfig(
                    verbose=True,
                    output_dir="confluence-ingest-output",
                    num_processes=2,
                ),
                read_config=ReadConfig(),
                partition_config=PartitionConfig(
                    metadata_exclude=["filename", "file_directory", "metadata.data_source.date_processed"],
                    partition_by_api=True,
                    api_key=os.getenv("UNSTRUCTURED_API_KEY"),
                ),
            )
            runner.run(
                url="https://unstructured-ingest-test.atlassian.net",
                user_email="12345678@unstructured.io",
                api_token="ABCDE1234ABDE1234ABCDE1234",
            )

Additionally, you will need to pass the ``--partition-endpoint`` if you're running the API locally. You can find more information about the ``unstructured`` API `here <https://github.com/Unstructured-IO/unstructured-api>`_.

For a full list of the options the CLI accepts check ``unstructured-ingest confluence --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
