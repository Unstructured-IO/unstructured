from unstructured.ingest.interfaces import BaseDestinationConnector, DatabricksVolumesConfig


def databricks_volumes_writer(
    auth_configs: dict,
    databricks_volume_config: DatabricksVolumesConfig,
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
            auth_configs=auth_configs, volume_configs=databricks_volume_config
        ),
    )
