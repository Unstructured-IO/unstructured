from unstructured.ingest.interfaces import BaseDestinationConnector, DatabricksVolumesConfig


def databricks_volumes_writer(
    auth_configs: dict,
    volume_configs: DatabricksVolumesConfig,
    overwrite: bool = False,
    **kwargs,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.databricks_volumes import (
        DatabricksVolumesDestinationConnector,
        DatabricksVolumesWriteConfig,
        SimpleDatabricksVolumesConfig,
    )

    return DatabricksVolumesDestinationConnector(
        write_config=DatabricksVolumesWriteConfig(overwrite=overwrite),
        connector_config=SimpleDatabricksVolumesConfig(
            auth_configs=auth_configs, volume_configs=volume_configs
        ),
    )
