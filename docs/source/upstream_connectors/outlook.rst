Outlook
==========
Connect Outlook to your preprocessing pipeline, and batch process all your documents using ``unstructured-ingest`` to store structured outputs locally on your filesystem.

First you'll need to install the Outlook dependencies as shown here.

.. code:: shell

  pip install "unstructured[outlook]"

Run Locally
-----------

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
            outlook \
            --client-id "$MS_CLIENT_ID" \
            --client-cred "$MS_CLIENT_CRED" \
            --tenant "$MS_TENANT_ID" \
            --user-email "$MS_USER_EMAIL" \
            --outlook-folders Inbox,"Sent Items" \
            --output-dir outlook-output \
            --num-processes 2 \
            --recursive \
            --verbose

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
            "outlook",
            "--client-id", "$MS_CLIENT_ID",
            "--client-cred", "$MS_CLIENT_CRED",
            "--tenant", "<Azure AD tenant_id, default is 'common'>",
            "--user-email", "$MS_USER_EMAIL",
            "--outlook-folders", "Inbox,Sent Items",
            "--output-dir", "onedrive-ingest-output",
            "--num-processes", "2",
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
          airtable \
          --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
          --personal-access-token "$AIRTABLE_PERSONAL_ACCESS_TOKEN" \
          --output-dir airtable-ingest-output \
          --num-processes 2 \
          --reprocess \
          --partition-by-api \
          --api-key "<UNSTRUCTURED-API-KEY>"

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
          "unstructured-ingest",
          "airtable",
          "--metadata-exclude", "filename,file_directory,metadata.data_source.date_processed",
          "--personal-access-token", "$AIRTABLE_PERSONAL_ACCESS_TOKEN",
          "--output-dir", "airtable-ingest-output"
          "--num-processes", "2",
          "--reprocess",
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

For a full list of the options the CLI accepts check ``unstructured-ingest outlook --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
