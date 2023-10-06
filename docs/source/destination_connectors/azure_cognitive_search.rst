Azure Cognitive Search
======================

Batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem and upload those local files to an Azure Cognitive Search index.

First you'll need to install the azure cognitive search dependencies as shown here.

.. code:: shell

  pip install "unstructured[azure-cognitive-search]"

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream s3 connector.

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
            s3 \
             --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
             --anonymous \
             --output-dir s3-small-batch-output-to-azure \
             --num-processes 2 \
             --verbose \
            --strategy fast \
            azure-cognitive-search \
            --key "$AZURE_SEARCH_API_KEY" \
            --endpoint "$AZURE_SEARCH_ENDPOINT" \
            --index utic-test-ingest-fixtures-output

   .. tab:: Python

      .. code:: python

        import os
        import subprocess

        command = [
            "unstructured-ingest",
            "s3",
            "--remote-url", "s3://utic-dev-tech-fixtures/small-pdf-set/",
            "--anonymous",
            "--output-dir", "s3-small-batch-output-to-azure",
            "--num-processes", "2",
            "--verbose",
            "--strategy", "fast",
            "azure-cognitive-search",
            "--key", os.getenv("AZURE_SEARCH_API_KEY"),
            "--endpoint", os.getenv("$AZURE_SEARCH_ENDPOINT"),
            "--index", "utic-test-ingest-fixtures-output",
        ]

        # Run the command
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        output, error = process.communicate()

        # Print output
        if process.returncode == 0:
            print("Command executed successfully. Output:")
            print(output.decode())
        else:
            print("Command failed. Error:")
            print(error.decode())


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> azure-cognitive-search --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.

Sample Index Schema
-------------------

To make sure the schema of the index matches the data being written to it, a sample schema json can be used:

.. literalinclude:: azure_cognitive_sample_index_schema.json
   :language: json
   :linenos:
   :caption: Object description
