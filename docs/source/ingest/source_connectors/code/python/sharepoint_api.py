import os

from unstructured.ingest.connector.sharepoint import (
    SharepointAccessConfig,
    SharepointPermissionsConfig,
    SimpleSharepointConfig,
)
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
        connector_config=SimpleSharepointConfig(
            access_config=SharepointAccessConfig(
                client_cred="<Microsoft Sharepoint app client-secret>",
            ),
            permissions_config=SharepointPermissionsConfig(
                application_id="<Microsoft Graph API application id>",
                client_cred="<Microsoft Graph API application credentials>",
                tenant="<e.g https://contoso.onmicrosoft.com to process permission "
                "info within tenant>",
            ),
            client_id="<Microsoft Sharepoint app client-id>",
            site="<e.g https://contoso.sharepoint.com to process all sites within tenant>",
            # Credentials to process data about permissions (rbac) within the tenant
            # Flag to process only files within the site(s)
            files_only=True,
            path="Shared Documents",
        ),
    )
    runner.run()
