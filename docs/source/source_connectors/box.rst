Box
==========
Connect Box to your preprocessing pipeline, and batch process all your documents using ``unstructured-ingest`` to store structured outputs locally on your filesystem.

First you'll need to install the Box dependencies as shown here.

.. code:: shell

  pip install "unstructured[box]"

Run Locally
-----------

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
          box \
          --box_app_config "$BOX_APP_CONFIG_PATH" \
          --remote-url box://utic-test-ingest-fixtures \
          --output-dir box-output \
          --num-processes 2 \
          --recursive \
          --verbose

   .. tab:: Python

      .. code:: python

        import os

        from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
        from unstructured.ingest.runner import BoxRunner

        if __name__ == "__main__":
            runner = BoxRunner(
                processor_config=ProcessorConfig(
                    verbose=True,
                    output_dir="box-output",
                    num_processes=2,
                ),
                read_config=ReadConfig(),
                partition_config=PartitionConfig(),
            )
            runner.run(
                box_app_config=os.getenv("BOX_APP_CONFIG_PATH"),
                recursive=True,
                remote_url="box://utic-test-ingest-fixtures",
            )

Run via the API
---------------

You can also use upstream connectors with the ``unstructured`` API. For this you'll need to use the ``--partition-by-api`` flag and pass in your API key with ``--api-key``.

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
          box \
          --box_app_config "$BOX_APP_CONFIG_PATH" \
          --remote-url box://utic-test-ingest-fixtures \
          --output-dir box-output \
          --num-processes 2 \
          --recursive \
          --verbose \
          --partition-by-api \
          --api-key "<UNSTRUCTURED-API-KEY>"

   .. tab:: Python

      .. code:: python

        import os

        from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
        from unstructured.ingest.runner import BoxRunner

        if __name__ == "__main__":
            runner = BoxRunner(
                processor_config=ProcessorConfig(
                    verbose=True,
                    output_dir="box-output",
                    num_processes=2,
                ),
                read_config=ReadConfig(),
                partition_config=PartitionConfig(
                    partition_by_api=True,
                    api_key=os.getenv("UNSTRUCTURED_API_KEY"),
                ),
            )
            runner.run(
                box_app_config=os.getenv("BOX_APP_CONFIG_PATH"),
                recursive=True,
                remote_url="box://utic-test-ingest-fixtures",
            )

Additionally, you will need to pass the ``--partition-endpoint`` if you're running the API locally. You can find more information about the ``unstructured`` API `here <https://github.com/Unstructured-IO/unstructured-api>`_.

For a full list of the options the CLI accepts check ``unstructured-ingest box --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
