Discord
==========
Connect Discord to your preprocessing pipeline, and batch process all your documents using ``unstructured-ingest`` to store structured outputs locally on your filesystem.

First you'll need to install the Discord dependencies as shown here.

.. code:: shell

  pip install "unstructured[discord]"

Run Locally
-----------

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
          discord \
          --channels 12345678 \
          --token "$DISCORD_TOKEN" \
          --download-dir discord-ingest-download \
          --output-dir discord-example \
          --preserve-downloads \
          --verbose

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
            "discord",
            "--channels", "12345678",
            "--token", "$DISCORD_TOKEN",
            "--download-dir", "discord-ingest-download",
            "--output-dir", "discord-example",
            "--preserve-downloads",
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
          discord \
          --channels 12345678 \
          --token "$DISCORD_TOKEN" \
          --download-dir discord-ingest-download \
          --output-dir discord-example \
          --preserve-downloads \
          --verbose \
          --partition-by-api \
          --api-key "<UNSTRUCTURED-API-KEY>"

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
          "discord",
          "--channels", "12345678",
          "--token", "$DISCORD_TOKEN",
          "--download-dir", "discord-ingest-download",
          "--output-dir", "discord-example",
          "--preserve-downloads",
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

For a full list of the options the CLI accepts check ``unstructured-ingest discord --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
