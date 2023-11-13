Pinecone
===========

Batch process all your records using ``unstructured-ingest`` to store structured outputs and embeddings locally on your filesystem and upload those to a Pinecone index.

First you'll need to install the Pinecone dependencies as shown here.

.. code:: shell

  pip install "unstructured[pinecone]"

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream s3 connector. This will create new files on your local.

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
            s3 \
            --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
            --anonymous \
            --output-dir s3-small-batch-output \
            --num-processes 2 \
            --verbose \
            --strategy fast \
            --chunk-elements \
            --embedding-provider <an unstructured embedding provider, ie. langchain-huggingface> \
            pinecone \
            --api-key <your pinecone api key here> \
            --index-name <your index name here, ie. ingest-test> \
            --environment <your environment name here, ie. gcp-starter>
            --batch-size <number of elements to be uploaded per batch, ie. 80>
            --num-processes <number of processes to be used to upload, ie. 2>

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
          "s3",
          "--remote-url", "s3://utic-dev-tech-fixtures/small-pdf-set/",
          "--anonymous",
          "--output-dir", "s3-small-batch-output \",
          "--num-processes", "2",
          "--verbose",
          "--strategy", "fast",
          "--embedding-api-key", "<your openai api key here>",
          "pinecone"
          "--api-key", "<your pinecone api key here>"
          "--index-name", "<your index name here, ie. ingest-test>"
          "--environment", "your environment name here, ie. gcp-starter"
        ]

        # Run the command
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        output, error = process.communicate()

        # Print output
        if process.returncode == 0:
            print('Command executed successfully. Output:')
            print(output.decode())
        else:
            print('Command failed. Error:')
            print(error.decode())


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> pinecone --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
