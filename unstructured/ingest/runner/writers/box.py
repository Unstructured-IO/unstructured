import typing as t

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.utils import requires_dependencies


@requires_dependencies(["boxfs", "fsspec"], extras="box")
def box_writer(
    remote_url: str,
    box_app_config: t.Optional[str],
    verbose: bool = False,
    **kwargs,
) -> BaseDestinationConnector:
    import boxsdk

    from unstructured.ingest.connector.box import (
        BoxDestinationConnector,
        SimpleBoxConfig,
    )
    from unstructured.ingest.connector.fsspec import FsspecWriteConfig

    access_kwargs: t.Dict[str, t.Any] = {"box_app_config": box_app_config}
    if verbose:
        access_kwargs["client_type"] = boxsdk.LoggingClient
    return BoxDestinationConnector(
        write_config=FsspecWriteConfig(),
        connector_config=SimpleBoxConfig(
            remote_url=remote_url,
            access_kwargs=access_kwargs,
        ),
    )
