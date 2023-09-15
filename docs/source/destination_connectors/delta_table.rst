Delta Table
==========
Batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem and upload those local files to a Delta Table.

First you'll need to install the delta table dependencies as shown here.

.. code:: shell

  pip install "unstructured[delta-table]"

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream delta-table connector. This will create a new table on your local and will raise an error if that table already exists.

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
            delta-table \
            --table-uri s3://utic-dev-tech-fixtures/sample-delta-lake-data/deltatable/ \
            --output-dir delta-table-example \
            --storage_options "AWS_REGION=us-east-2,AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
            --verbose
            delta-table \
            --write-column json_data \
            --table-uri delta-table-dest

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
          "delta-table",
          "--table-uri", "s3://utic-dev-tech-fixtures/sample-delta-lake-data/deltatable/",
          "--download-dir", "delta-table-ingest-download",
          "--output-dir", "delta-table-example",
          "--preserve-downloads",
          "--storage_options", "AWS_REGION=us-east-2,AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY",
          "--verbose",
          "delta-table"
          "--write-column json_data"
          "--table-uri delta-table-dest"
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


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> delta-table --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
