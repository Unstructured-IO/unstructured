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
            s3 \
            --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
            --anonymous \
            --output-dir s3-small-batch-output-to-sql \
            --num-processes 2 \
            --verbose \
            --strategy fast \
            weaviate \
            --host-url http://localhost:8080 \
            --class-name elements \

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
          "s3",
          "--remote-url", "s3://utic-dev-tech-fixtures/small-pdf-set/",
          "--anonymous",
          "--output-dir", "s3-small-batch-output-to-postgresql",
          "--num-processes", "2",
          "--verbose",
          "--strategy", "fast",
          "weaviate"
          "--host-url http://localhost:808"
          "--class-name elements"
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


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> weaviate --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
