from unstructured.ingest.connector.onedrive import OneDriveAccessConfig, SimpleOneDriveConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import OneDriveRunner

if __name__ == "__main__":
    runner = OneDriveRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="onedrive-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleOneDriveConfig(
            access_config=OneDriveAccessConfig(client_credential="<Azure AD app client-id>"),
            client_id="<Azure AD app client-id>",
            authority_url="<Authority URL, default is https://login.microsoftonline.com>",
            tenant="<Azure AD tenant_id, default is 'common'>",
            user_pname="<Azure AD principal name, in most cases is the email linked to the drive>",
            path="<Path to start parsing files from>",
            recursive=False,
        ),
    )
    runner.run()
