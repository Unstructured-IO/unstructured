One Drive
==========
Connect One Drive to your preprocessing pipeline, and batch process all your documents using ``unstructured-ingest`` to store structured outputs locally on your filesystem.

First you'll need to install the Airtable dependencies as shown here.

.. code:: shell

  pip install "unstructured[onedrive]"

Run Locally
-----------

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
            onedrive \
            --client-id "<Azure AD app client-id>" \
            --client-cred "<Azure AD app client-secret>" \
            --authority-url "<Authority URL, default is https://login.microsoftonline.com>" \
            --tenant "<Azure AD tenant_id, default is 'common'>" \
            --user-pname "<Azure AD principal name, in most cases is the email linked to the drive>" \
            --path "<Path to start parsing files from>" \
            --output-dir onedrive-ingest-output \
            --num-processes 2 \
            --verbose

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
            "unstructured-ingest",
                "onedrive",
                "--client-id", "<Azure AD app client-id>",
                "--client-cred", "<Azure AD app client-secret>",
                "--authority-url", "<Authority URL, default is https://login.microsoftonline.com>",
                "--tenant", "<Azure AD tenant_id, default is 'common'>",
                "--user-pname", "<Azure AD principal name, in most cases is the email linked to the drive>",
                "--path", "<Path to start parsing files from>",
                "--output-dir", "onedrive-ingest-output",
                "--num-processes", "2",
                "--verbose"
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
            onedrive \
            --client-id "<Azure AD app client-id>" \
            --client-cred "<Azure AD app client-secret>" \
            --authority-url "<Authority URL, default is https://login.microsoftonline.com>" \
            --tenant "<Azure AD tenant_id, default is 'common'>" \
            --user-pname "<Azure AD principal name, in most cases is the email linked to the drive>" \
            --path "<Path to start parsing files from>" \
            --output-dir onedrive-ingest-output \
            --num-processes 2 \
            --verbose \
            --partition-by-api \
            --api-key "<UNSTRUCTURED-API-KEY>"

   .. tab:: Python

      .. code:: python

        import subprocess

        command = [
            "unstructured-ingest",
                "onedrive",
                "--client-id", "<Azure AD app client-id>",
                "--client-cred", "<Azure AD app client-secret>",
                "--authority-url", "<Authority URL, default is https://login.microsoftonline.com>",
                "--tenant", "<Azure AD tenant_id, default is 'common'>",
                "--user-pname", "<Azure AD principal name, in most cases is the email linked to the drive>",
                "--path", "<Path to start parsing files from>",
                "--output-dir", "onedrive-ingest-output",
                "--num-processes", "2",
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

For a full list of the options the CLI accepts check ``unstructured-ingest onedrive --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
