from unstructured.ingest.interfaces import StandardConnectorConfig


def map_to_standard_config(ctx_dict: dict) -> StandardConnectorConfig:
    return StandardConnectorConfig(
        download_dir=ctx_dict["download_dir"],
        output_dir=ctx_dict["structured_output_dir"],
        download_only=ctx_dict["download_only"],
        fields_include=ctx_dict["fields_include"],
        flatten_metadata=ctx_dict["flatten_metadata"],
        metadata_exclude=ctx_dict["metadata_exclude"],
        metadata_include=ctx_dict["metadata_include"],
        partition_by_api=ctx_dict["partition_by_api"],
        partition_endpoint=ctx_dict["partition_endpoint"],
        preserve_downloads=ctx_dict["preserve_downloads"],
        re_download=ctx_dict["re_download"],
        api_key=ctx_dict["api_key"],
    )
