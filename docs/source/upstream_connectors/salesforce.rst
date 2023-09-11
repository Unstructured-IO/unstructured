Salesforce
==========
Connect Salesforce to your preprocessing pipeline, and batch process Salesforce data using ``unstructured-ingest`` to store structured outputs locally on your filesystem.

First you'll need to install the Salesforce dependencies as shown here.

.. code:: shell

  pip install "unstructured[salesforce]"

Run Locally
-----------

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
          salesforce \
          --username "$SALESFORCE_USERNAME" \
          --consumer-key "$SALESFORCE_CONSUMER_KEY" \
          --private-key-path "$SALESFORCE_PRIVATE_KEY_PATH" \
          --categories "EmailMessage,Account,Lead,Case,Campaign" \
          --output-dir salesforce-output \
          --num-processes 2 \
          --recursive \
          --verbose

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
          "salesforce",
          "--username" "$SALESFORCE_USERNAME"
          "--consumer-key" "$SALESFORCE_CONSUMER_KEY"
          "--private-key-path" "$SALESFORCE_PRIVATE_KEY_PATH"
          "--categories" "EmailMessage,Account,Lead,Case,Campaign"
          "--output-dir" "salesforce-output"
          "--num-processes", "2"
          "--recursive",
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
          salesforce \
          --username "$SALESFORCE_USERNAME" \
          --consumer-key "$SALESFORCE_CONSUMER_KEY" \
          --private-key-path "$SALESFORCE_PRIVATE_KEY_PATH" \
          --categories "EmailMessage,Account,Lead,Case,Campaign" \
          --output-dir salesforce-output \
          --num-processes 2 \
          --recursive \
          --verbose
          --partition-by-api \
          --api-key "<UNSTRUCTURED-API-KEY>"

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
          "salesforce",
          "--username" "$SALESFORCE_USERNAME"
          "--consumer-key" "$SALESFORCE_CONSUMER_KEY"
          "--private-key-path" "$SALESFORCE_PRIVATE_KEY_PATH"
          "--categories" "EmailMessage,Account,Lead,Case,Campaign"
          "--output-dir" "salesforce-output"
          "--num-processes", "2"
          "--recursive",
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

For a full list of the options the CLI accepts check ``unstructured-ingest salesforce --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
