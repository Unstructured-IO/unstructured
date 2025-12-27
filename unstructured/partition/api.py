from __future__ import annotations

import contextlib
from typing import IO, Any, Optional, Sequence

import requests
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations, shared
from unstructured_client.utils import retries

from unstructured.documents.elements import Element
from unstructured.logger import logger
from unstructured.partition.common.common import exactly_one
from unstructured.staging.base import elements_from_dicts, elements_from_json

# Default retry configuration taken from the client code
DEFAULT_RETRIES_INITIAL_INTERVAL_SEC = 3000
DEFAULT_RETRIES_MAX_INTERVAL_SEC = 720000
DEFAULT_RETRIES_EXPONENT = 1.5
DEFAULT_RETRIES_MAX_ELAPSED_TIME_SEC = 1800000
DEFAULT_RETRIES_CONNECTION_ERRORS = True


def partition_via_api(
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    file_filename: Optional[str] = None,
    api_url: str = "https://api.unstructured.io/general/v0/general",
    api_key: str = "",
    metadata_filename: Optional[str] = None,
    retries_initial_interval: [int] = None,
    retries_max_interval: Optional[int] = None,
    retries_exponent: Optional[float] = None,
    retries_max_elapsed_time: Optional[int] = None,
    retries_connection_errors: Optional[bool] = None,
    **request_kwargs: Any,
) -> list[Element]:
    """Partitions a document using the Unstructured REST API. This is equivalent to
    running the document through partition.

    See https://api.unstructured.io/general/docs for the hosted API documentation or
    https://github.com/Unstructured-IO/unstructured-api for instructions on how to run
    the API locally as a container.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    content_type
        A string defining the file content in MIME type
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    metadata_filename
        When file is not None, the filename (string) to store in element metadata. E.g. "foo.txt"
    api_url
        The URL for the Unstructured API. Defaults to the hosted Unstructured API.
    api_key
        The API key to pass to the Unstructured API.
    retries_initial_interval
        Defines the time interval (in seconds) to wait before the first retry in case of a request
        failure. Defaults to 3000. If set should be > 0.
    retries_max_interval
        Defines the maximum time interval (in seconds) to wait between retries (the interval
        between retries is increased as using exponential increase algorithm
        - this setting limits it). Defaults to 720000. If set should be > 0.
    retries_exponent
        Defines the exponential factor to increase the interval between retries. Defaults to 1.5.
        If set should be > 0.0.
    retries_max_elapsed_time
        Defines the maximum time (in seconds) to wait for retries. If exceeded, the original
        exception is raised. Defaults to 1800000. If set should be > 0.
    retries_connection_errors
        Defines whether to retry on connection errors. Defaults to True.
    request_kwargs
        Additional parameters to pass to the data field of the request to the Unstructured API.
        For example the `strategy` parameter.
    """
    exactly_one(filename=filename, file=file)

    if metadata_filename and file_filename:
        raise ValueError(
            "Only one of metadata_filename and file_filename is specified. "
            "metadata_filename is preferred. file_filename is marked for deprecation.",
        )

    if file_filename is not None:
        metadata_filename = file_filename
        logger.warning(
            "The file_filename kwarg will be deprecated in a future version of unstructured. "
            "Please use metadata_filename instead.",
        )

    # Note(austin) - the sdk takes the base url, but we have the full api_url
    # For consistency, just strip off the path when it's given
    base_url = api_url[:-19] if "/general/v0/general" in api_url else api_url
    sdk = UnstructuredClient(api_key_auth=api_key, server_url=base_url)

    if filename is not None:
        with open(filename, "rb") as f:
            files = shared.Files(
                content=f.read(),
                file_name=filename,
            )

    elif file is not None:
        if metadata_filename is None:
            raise ValueError(
                "If file is specified in partition_via_api, "
                "metadata_filename must be specified as well.",
            )
        files = shared.Files(content=file, file_name=metadata_filename)

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(files=files, **request_kwargs)
    )

    retries_config = get_retries_config(
        retries_connection_errors=retries_connection_errors,
        retries_exponent=retries_exponent,
        retries_initial_interval=retries_initial_interval,
        retries_max_elapsed_time=retries_max_elapsed_time,
        retries_max_interval=retries_max_interval,
        sdk=sdk,
    )

    response = sdk.general.partition(
        request=req,
        retries=retries_config,
    )

    if response.status_code == 200:
        return elements_from_json(text=response.raw_response.text)
    else:
        raise ValueError(
            f"Receive unexpected status code {response.status_code} from the API.",
        )


def get_retries_config(
    retries_connection_errors: Optional[bool],
    retries_exponent: Optional[float],
    retries_initial_interval: Optional[int],
    retries_max_elapsed_time: Optional[int],
    retries_max_interval: Optional[int],
    sdk: UnstructuredClient,
) -> Optional[retries.RetryConfig]:
    """Constructs a RetryConfig object from the provided parameters. If any of the parameters
    are None, the default values are taken from the SDK configuration or the default constants.

    If all parameters are None, returns None (and the SDK-managed defaults are used within the
    client)

    The solution is not perfect as the RetryConfig object does not include the defaults by
    itself so we might need to construct it basing on our defaults.

    Parameters
    ----------
    retries_connection_errors
        Defines whether to retry on connection errors. If not set the
        DEFAULT_RETRIES_CONNECTION_ERRORS constant is used.
    retries_exponent
        Defines the exponential factor to increase the interval between retries.
        If set, should be > 0.0 (otherwise the DEFAULT_RETRIES_EXPONENT constant is used)
    retries_initial_interval
        Defines the time interval to wait before the first retry in case of a request failure.
        If set, should be > 0 (otherwise the DEFAULT_RETRIES_INITIAL_INTERVAL_SEC constant is used)
    retries_max_elapsed_time
        Defines the maximum time to wait for retries. If exceeded, the original exception is raised.
        If set, should be > 0 (otherwise the DEFAULT_RETRIES_MAX_ELAPSED_TIME_SEC constant is used)
    retries_max_interval
        Defines the maximum time interval to wait between retries. If set, should be > 0
        (otherwise the DEFAULT_RETRIES_MAX_INTERVAL_SEC constant is used)
    sdk
        The UnstructuredClient object to take the default values from.
    """
    retries_config = None
    sdk_default_retries_config = sdk.sdk_configuration.retry_config
    if any(
        setting is not None
        for setting in (
            retries_initial_interval,
            retries_max_interval,
            retries_exponent,
            retries_max_elapsed_time,
            retries_connection_errors,
        )
    ):

        def get_backoff_default(setting_name: str, default_value: Any) -> Any:
            if sdk_default_retries_config:  # noqa: SIM102
                if setting_value := getattr(sdk_default_retries_config.backoff, setting_name):
                    return setting_value
            return default_value

        default_retries_connneciton_errors = (
            sdk_default_retries_config.retry_connection_errors
            if sdk_default_retries_config
            and sdk_default_retries_config.retry_connection_errors is not None
            else DEFAULT_RETRIES_CONNECTION_ERRORS
        )

        backoff_strategy = retries.BackoffStrategy(
            initial_interval=(
                retries_initial_interval
                or get_backoff_default("initial_interval", DEFAULT_RETRIES_INITIAL_INTERVAL_SEC)
            ),
            max_interval=(
                retries_max_interval
                or get_backoff_default("max_interval", DEFAULT_RETRIES_MAX_INTERVAL_SEC)
            ),
            exponent=(
                retries_exponent or get_backoff_default("exponent", DEFAULT_RETRIES_EXPONENT)
            ),
            max_elapsed_time=(
                retries_max_elapsed_time
                or get_backoff_default("max_elapsed_time", DEFAULT_RETRIES_MAX_ELAPSED_TIME_SEC)
            ),
        )
        retries_config = retries.RetryConfig(
            strategy="backoff",
            backoff=backoff_strategy,
            retry_connection_errors=(
                retries_connection_errors
                if retries_connection_errors is not None
                else default_retries_connneciton_errors
            ),
        )
    return retries_config


def partition_multiple_via_api(
    filenames: Optional[list[str]] = None,
    content_types: Optional[list[str]] = None,
    files: Optional[Sequence[IO[bytes]]] = None,
    file_filenames: Optional[list[str]] = None,
    api_url: str = "https://api.unstructured.io/general/v0/general",
    api_key: str = "",
    metadata_filenames: Optional[list[str]] = None,
    **request_kwargs: Any,
) -> list[list[Element]]:
    """Partitions multiple documents using the Unstructured REST API by batching
    the documents into a single HTTP request.

    See https://api.unstructured.io/general/docs for the hosted API documentation or
    https://github.com/Unstructured-IO/unstructured-api for instructions on how to run
    the API locally as a container.

    Parameters
    ----------
    filenames
        A list of strings defining the target filename paths.
    content_types
        A list of strings defining the file contents in MIME types.
    files
        A list of file-like object using "rb" mode --> open(filename, "rb").
    metadata_filename
        When file is not None, the filename (string) to store in element metadata. E.g. "foo.txt"
    api_url
        The URL for the Unstructured API. Defaults to the hosted Unstructured API.
    api_key
        The API key to pass to the Unstructured API.
    request_kwargs
        Additional parameters to pass to the data field of the request to the Unstructured API.
        For example the `strategy` parameter.
    """
    headers = {
        "ACCEPT": "application/json",
        "UNSTRUCTURED-API-KEY": api_key,
    }

    if metadata_filenames and file_filenames:
        raise ValueError(
            "Only one of metadata_filenames and file_filenames is specified. "
            "metadata_filenames is preferred. file_filenames is marked for deprecation.",
        )

    if file_filenames is not None:
        metadata_filenames = file_filenames
        logger.warning(
            "The file_filenames kwarg will be deprecated in a future version of unstructured. "
            "Please use metadata_filenames instead.",
        )

    if filenames is not None:
        if content_types and len(content_types) != len(filenames):
            raise ValueError("content_types and filenames must have the same length.")

        with contextlib.ExitStack() as stack:
            files = [stack.enter_context(open(f, "rb")) for f in filenames]  # type: ignore

            _files = []
            for i, file in enumerate(files):
                filename = filenames[i]
                content_type = content_types[i] if content_types is not None else None
                _files.append(("files", (filename, file, content_type)))

            response = requests.post(
                api_url,
                headers=headers,
                data=request_kwargs,
                files=_files,  # type: ignore
            )

    elif files is not None:
        if content_types and len(content_types) != len(files):
            raise ValueError("content_types and files must have the same length.")

        if not metadata_filenames:
            raise ValueError("metadata_filenames must be specified if files are passed")
        elif len(metadata_filenames) != len(files):
            raise ValueError("metadata_filenames and files must have the same length.")

        _files = []
        for i, _file in enumerate(files):  # type: ignore
            content_type = content_types[i] if content_types is not None else None
            filename = metadata_filenames[i]
            _files.append(("files", (filename, _file, content_type)))

        response = requests.post(
            api_url,
            headers=headers,
            data=request_kwargs,
            files=_files,  # type: ignore
        )

    if response.status_code == 200:
        documents = []
        response_list = response.json()
        # NOTE(robinson) - this check is because if only one filename is passed, the return
        # type from the API is a list of objects instead of a list of lists
        if not isinstance(response_list[0], list):
            response_list = [response_list]

        for document in response_list:
            documents.append(elements_from_dicts(document))
        return documents
    else:
        raise ValueError(
            f"Receive unexpected status code {response.status_code} from the API.",
        )
