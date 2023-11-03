Sharepoint
==========
Connect Sharepoint to your preprocessing pipeline, and batch process all your documents using ``unstructured-ingest`` to store structured outputs locally on your filesystem.

First you'll need to install the Sharepoint dependencies as shown here.

.. code:: shell

  pip install "unstructured[sharepoint]"

Run Locally
-----------

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
          sharepoint \
          --client-id "<Microsoft Sharepoint app client-id>" \
          --client-cred "<Microsoft Sharepoint app client-secret>" \
          --site "<e.g https://contoso.sharepoint.com or https://contoso.admin.sharepoint.com to process all sites within tenant>" \
          --permissions-application-id "<Microsoft Graph API application id, to process per-file access permissions>" \
          --permissions-client-cred "<Microsoft Graph API application credentials, to process per-file access permissions>" \
          --permissions-tenant "<e.g https://contoso.onmicrosoft.com (tenant URL) to process per-file access permissions>" \
          --files-only "Flag to process only files within the site(s)" \
          --output-dir sharepoint-ingest-output \
          --num-processes 2 \
          --path "Shared Documents" \
          --verbose

   .. tab:: Python

      .. code:: python

        import os

        from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
        from unstructured.ingest.runner import SharePointRunner

        if __name__ == "__main__":
            runner = SharePointRunner(
                processor_config=ProcessorConfig(
                    verbose=True,
                    output_dir="sharepoint-ingest-output",
                    num_processes=2,
                ),
                read_config=ReadConfig(),
                partition_config=PartitionConfig(),
            )
            runner.run(
                client_id="<Microsoft Sharepoint app client-id>",
                client_cred="<Microsoft Sharepoint app client-secret>",
                site="<e.g https://contoso.sharepoint.com to process all sites within tenant>",
                # Credentials to process data about permissions (rbac) within the tenant
                permissions_application_id="<Microsoft Graph API application id>",
                permissions_client_cred="<Microsoft Graph API application credentials>",
                permissions_tenant="<e.g https://contoso.onmicrosoft.com to process permission info within tenant>",
                # Flag to process only files within the site(s)
                files_only=True,
                path="Shared Documents",
            )

Run via the API
---------------

You can also use upstream connectors with the ``unstructured`` API. For this you'll need to use the ``--partition-by-api`` flag and pass in your API key with ``--api-key``.

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
          sharepoint \
          --client-id "<Microsoft Sharepoint app client-id>" \
          --client-cred "<Microsoft Sharepoint app client-secret>" \
          --site "<e.g https://contoso.sharepoint.com or https://contoso.admin.sharepoint.com to process all sites within tenant>" \
          --permissions-application-id "<Microsoft Graph API application id, to process per-file access permissions>" \
          --permissions-client-cred "<Microsoft Graph API application credentials, to process per-file access permissions>" \
          --permissions-tenant "<e.g https://contoso.onmicrosoft.com (tenant URL) to process per-file access permissions>" \
          --files-only "Flag to process only files within the site(s)" \
          --output-dir sharepoint-ingest-output \
          --num-processes 2 \
          --verbose \
          --path "Shared Documents" \
          --partition-by-api \
          --api-key "<UNSTRUCTURED-API-KEY>"

   .. tab:: Python

      .. code:: python

        import os

        from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
        from unstructured.ingest.runner import SharePointRunner

        if __name__ == "__main__":
            runner = SharePointRunner(
                processor_config=ProcessorConfig(
                    verbose=True,
                    output_dir="sharepoint-ingest-output",
                    num_processes=2,
                ),
                read_config=ReadConfig(),
                partition_config=PartitionConfig(
                    partition_by_api=True,
                    api_key=os.getenv("UNSTRUCTURED_API_KEY"),
                ),
            )
            runner.run(
                client_id="<Microsoft Sharepoint app client-id>",
                client_cred="<Microsoft Sharepoint app client-secret>",
                site="<e.g https://contoso.sharepoint.com to process all sites within tenant>",
                # Credentials to process data about permissions (rbac) within the tenant
                permissions_application_id="<Microsoft Graph API application id>",
                permissions_client_cred="<Microsoft Graph API application credentials>",
                permissions_tenant="<e.g https://contoso.onmicrosoft.com to process permission info within tenant>",
                # Flag to process only files within the site(s)
                files_only=True,
                path="Shared Documents",
            )

Additionally, you will need to pass the ``--partition-endpoint`` if you're running the API locally. You can find more information about the ``unstructured`` API `here <https://github.com/Unstructured-IO/unstructured-api>`_.

For a full list of the options the CLI accepts check ``unstructured-ingest sharepoint --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
