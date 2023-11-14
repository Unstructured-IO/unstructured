MongoDB
======================

Batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem and upload those local files to an MongoDB collection.

First you'll need to install the azure cognitive search dependencies as shown here.

.. code:: shell

  pip install "unstructured[mongodb]"

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream local connector.

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
            local \
            --input-path example-docs/fake-memo.pdf \
            --anonymous \
            --output-dir local-output-to-mongo \
            --num-processes 2 \
            --verbose \
            --strategy fast \
            mongodb \
            --uri "$MONGODB_URI" \
            --database "$MONGODB_DATABASE_NAME" \
            --collection "$DESTINATION_MONGO_COLLECTION"

   .. tab:: Python

      .. code:: python

        import os

        from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
        from unstructured.ingest.runner import LocalRunner

        if __name__ == "__main__":
            runner = LocalRunner(
                processor_config=ProcessorConfig(
                    verbose=True,
                    output_dir="local-output-to-mongo",
                    num_processes=2,
                ),
                read_config=ReadConfig(),
                partition_config=PartitionConfig(),
                writer_type="mongodb",
                writer_kwargs={
                    "uri": os.getenv("MONGODB_URI"),
                    "database": os.getenv("MONGODB_DATABASE_NAME"),
                    "collection": os.getenv("DESTINATION_MONGO_COLLECTION")
                }
            )
            runner.run(
                input_path="example-docs/fake-memo.pdf",
            )


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> mongodb --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
