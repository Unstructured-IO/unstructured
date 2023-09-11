from unstructured.ingest.interfaces import WriteConfig


def s3_writer(
    remote_url: str,
    anonymous: bool,
    verbose: bool = False,
):
    from unstructured.ingest.connector.s3 import (
        S3DestinationConnector,
        SimpleS3Config,
    )

    return S3DestinationConnector(
        write_config=WriteConfig(),
        connector_config=SimpleS3Config(
            path=remote_url,
            access_kwargs={"anon": anonymous},
        ),
    )


writer_map = {
    "s3": s3_writer,
}
