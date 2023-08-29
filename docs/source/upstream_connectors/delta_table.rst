Delta Table
==========
Connect delta tables to your preprocessing pipeline, and batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem.

First you'll need to install the delta table dependencies as shown here.

.. code:: shell

  pip install "unstructured[delta-table]"

Run Locally
-----------

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
            delta-table \
            --table-uri s3://utic-dev-tech-fixtures/sample-delta-lake-data/deltatable/ \
            --structured-output-dir delta-table-example \
            --storage_options "AWS_REGION=us-east-2,AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
            --verbose

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
          "delta-table",
          "--table-uri", "s3://utic-dev-tech-fixtures/sample-delta-lake-data/deltatable/",
          "--download-dir", "delta-table-ingest-download",
          "--structured-output-dir", "delta-table-example",
          "--preserve-downloads",
          "--storage_options", "AWS_REGION=us-east-2,AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY",
          "--verbose",
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

Run via the API
---------------

You can also use upstream connectors with the ``unstructured`` API. For this you'll need to use the ``--partition-by-api`` flag and pass in your API key with ``--api-key``.

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
          delta-table \
          --table-uri s3://utic-dev-tech-fixtures/sample-delta-lake-data/deltatable/ \
          --structured-output-dir delta-table-example \
          --storage_options "AWS_REGION=us-east-2,AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
          --verbose
          --partition-by-api \
          --api-key "<UNSTRUCTURED-API-KEY>"

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
          "delta-table",
          "--table-uri", "s3://utic-dev-tech-fixtures/sample-delta-lake-data/deltatable/",
          "--download-dir", "delta-table-ingest-download",
          "--structured-output-dir", "delta-table-example",
          "--preserve-downloads",
          "--storage_options", "AWS_REGION=us-east-2,AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY",
          "--verbose",
          "--partition-by-api",
          "--api-key", "<UNSTRUCTURED-API-KEY>",
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

Additionally, you will need to pass the ``--partition-endpoint`` if you're running the API locally. You can find more information about the ``unstructured`` API `here <https://github.com/Unstructured-IO/unstructured-api>`_.

For a full list of the options the CLI accepts check ``unstructured-ingest delta-table --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
