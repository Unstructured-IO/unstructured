Pinecone
===========

Batch process all your records using ``unstructured-ingest`` to store structured outputs and embeddings locally on your filesystem and upload those to a Pinecone index.

First you'll need to install the Pinecone dependencies as shown here.

.. code:: shell

  pip install "unstructured[pinecone]"

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
            pinecone \
            --api-key <your pinecone api key here> \
            --index-name <your index name here, ie. ingest-test> \
            --environment <your environment name here, ie. gcp-starter> \
            --batch-size <number of elements to be uploaded per batch, ie. 80> \
            --num-processes <number of processes to be used to upload, ie. 2>

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
                writer_type="pinecone",
                writer_kwargs={
                    "api_key": os.getenv("PINECONE_API_KEY"),
                    "index_name": os.getenv("PINECONE_INDEX_NAME"),
                    "environment": os.getenv("PINECONE_ENVIRONMENT_NAME"),
                    "batch_size": 80,
                    "num_processes": 2,
                }
            )
            runner.run(
                input_path="example-docs/fake-memo.pdf",
            )


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> pinecone --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
