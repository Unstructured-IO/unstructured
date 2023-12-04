Weaviate
===========

Batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem and upload those local files to a Weaviate collection.

First you'll need to install the weaviate dependencies as shown here.

.. code:: shell

  pip install "unstructured[weaviate]"

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream weaviate connector. This will push elements into a collection schema of your choice into a weaviate instance
running locally.

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
            local \
            --input-path example-docs/fake-memo.pdf \
            --anonymous \
            --output-dir local-output-to-weaviate \
            --num-processes 2 \
            --verbose \
            --strategy fast \
            weaviate \
            --host-url http://localhost:8080 \
            --class-name elements \

   .. tab:: Python

      .. code:: python

        import os

        from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
        from unstructured.ingest.runner import LocalRunner

        if __name__ == "__main__":
            runner = LocalRunner(
                processor_config=ProcessorConfig(
                    verbose=True,
                    output_dir="local-output-to-weaviate",
                    num_processes=2,
                ),
                read_config=ReadConfig(),
                partition_config=PartitionConfig(),
                writer_type="weaviate",
                writer_kwargs={
                    "host_url": os.getenv("WEAVIATE_HOST_URL"),
                    "class_name": os.getenv("WEAVIATE_CLASS_NAME")
                }
            )
            runner.run(
                input_path="example-docs/fake-memo.pdf",
            )


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> weaviate --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
