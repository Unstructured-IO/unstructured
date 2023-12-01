SQL
===========
NOTE: At the moment, the connector only supports PostgreSQL and SQLite.

Batch process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem and upload those local files to a PostgreSQL or SQLite schema.

First you'll need to install the sql dependencies as shown here.

.. code:: shell

  pip install "unstructured[sql]"

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream s3 connector.

.. tabs::

   .. tab:: Shell - with parameters
    
    You can use the connectors with the same parameters used in `sqlalchemy.engine.URL.create <https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.engine.URL.create>`_

      .. code:: shell

        unstructured-ingest \
            local \
            --input-path example-docs/fake-memo.pdf \
            --anonymous \
            --output-dir local-output-to-mongo \
            --num-processes 2 \
            --verbose \
            --strategy fast \
            sql \
            --db_name postgresql \
            --username postgres \
            --password test \
            --host localhost \
            --port 5432 \
            --database elements

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
          "local",
          "--input-path", "example-docs/fake-memo.pdf",
          "--anonymous",
          "--output-dir", "local-output-to-mongo"
          "--num-processes", "2"
          "--verbose"
          "--strategy", "fast",
          "sql"
          "--db_name postgresql"
          "--username postgres"
          "--password test"
          "--host localhost"
          "--port 5432"
          "--database elements"
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


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> sql --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
