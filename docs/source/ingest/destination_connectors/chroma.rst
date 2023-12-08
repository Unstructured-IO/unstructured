Chroma
======================

Batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem and upload those to a Chroma database.

First you'll need to install the Chroma dependencies as shown here.

.. code:: shell

  pip install "unstructured[chroma]"

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream local connector. This will create new files on your local.

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
            local \
            --input-path example-docs/book-war-and-peace-1225p.txt \
            --output-dir local-to-pinecone \
            --strategy fast \
            --chunk-elements \
            --embedding-provider <an unstructured embedding provider, ie. langchain-huggingface> \
            --num-processes 2 \
            --verbose \
            --work-dir "<directory for intermediate outputs to be saved>" \
            chroma \
            --db-path "$DESTINATION_PATH" \
            --collection-name "$COLLECTION_NAME" \
            --batch-size 80

   .. tab:: Python

      .. code:: python

        import os

        from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig, ChunkingConfig, EmbeddingConfig
        from unstructured.ingest.runner import LocalRunner
        if __name__ == "__main__":
            runner = LocalRunner(
                processor_config=ProcessorConfig(
                    verbose=True,
                    output_dir="local-output-to-pinecone",
                    num_processes=2,
                ),
                read_config=ReadConfig(),
                partition_config=PartitionConfig(),
                chunking_config=ChunkingConfig(
                  chunk_elements=True
                ),
                embedding_config=EmbeddingConfig(
                  provider="langchain-huggingface",
                ),
                writer_type="chroma",
                writer_kwargs={
                    "db_path": os.getenv("DESTINATION_PATH"),
                    "collection_name": os.getenv("COLLECTION_NAME"),
                    "batch_size": 80,
                }
            )
            runner.run(
                input_path="example-docs/fake-memo.pdf",
            )


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> chroma --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.