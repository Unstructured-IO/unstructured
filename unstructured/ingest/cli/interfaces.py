import json
import os.path
import typing as t
from abc import abstractmethod
from dataclasses import fields
from gettext import gettext, ngettext
from pathlib import Path

import click
from dataclasses_json.core import Json, _decode_dataclass

from unstructured.ingest.interfaces import (
    BaseConfig,
    ChunkingConfig,
    EmbeddingConfig,
    FileStorageConfig,
    PartitionConfig,
    PermissionsConfig,
    ProcessorConfig,
    ReadConfig,
    RetryStrategyConfig,
)


class Dict(click.ParamType):
    name = "dict"

    def convert(
        self,
        value: t.Any,
        param: t.Optional[click.Parameter],
        ctx: t.Optional[click.Context],
    ) -> t.Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            self.fail(
                gettext(
                    "{value} is not a valid json value.",
                ).format(value=value),
                param,
                ctx,
            )


class FileOrJson(click.ParamType):
    name = "file-or-json"

    def convert(
        self,
        value: t.Any,
        param: t.Optional[click.Parameter],
        ctx: t.Optional[click.Context],
    ) -> t.Any:
        # check if valid file
        full_path = os.path.abspath(os.path.expanduser(value))
        if os.path.isfile(full_path):
            return str(Path(full_path).resolve())
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        self.fail(
            gettext(
                "{value} is not a valid json string nor an existing filepath.",
            ).format(value=value),
            param,
            ctx,
        )


class DelimitedString(click.ParamType):
    name = "delimited-string"

    def __init__(self, delimiter: str = ",", choices: t.Optional[t.List[str]] = None):
        self.choices = choices if choices else []
        self.delimiter = delimiter

    def convert(
        self,
        value: t.Any,
        param: t.Optional[click.Parameter],
        ctx: t.Optional[click.Context],
    ) -> t.Any:
        # In case a list is provided as the default, will not break
        if isinstance(value, list):
            split = [str(v).strip() for v in value]
        else:
            split = [v.strip() for v in value.split(self.delimiter)]
        if not self.choices:
            return split
        choices_str = ", ".join(map(repr, self.choices))
        for s in split:
            if s not in self.choices:
                self.fail(
                    ngettext(
                        "{value!r} is not {choice}.",
                        "{value!r} is not one of {choices}.",
                        len(self.choices),
                    ).format(value=s, choice=choices_str, choices=choices_str),
                    param,
                    ctx,
                )
        return split


class CliMixin:
    @staticmethod
    @abstractmethod
    def get_cli_options() -> t.List[click.Option]:
        pass

    @classmethod
    def add_cli_options(cls, cmd: click.Command) -> None:
        options_to_add = cls.get_cli_options()
        CliMixin.add_params(cmd, params=options_to_add)

    def add_params(cmd: click.Command, params: t.List[click.Parameter]):
        existing_opts = []
        for param in cmd.params:
            existing_opts.extend(param.opts)

        for param in params:
            for opt in param.opts:
                if opt in existing_opts:
                    raise ValueError(f"{opt} is already defined on the command {cmd.name}")
                existing_opts.append(opt)
                cmd.params.append(param)


class CliConfig(BaseConfig, CliMixin):
    pass


class CliRetryStrategyConfig(RetryStrategyConfig, CliMixin):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--max-retries"],
                default=None,
                type=int,
                help="If provided, will use this max retry for "
                "back off strategy if http calls fail",
            ),
            click.Option(
                ["--max-retry-time"],
                default=None,
                type=float,
                help="If provided, will attempt retries for this long as part "
                "of back off strategy if http calls fail",
            ),
        ]
        return options

    @classmethod
    def from_dict(
        cls,
        kvs: Json,
        *,
        infer_missing=False,
    ):
        """
        Return None if none of the fields are being populated
        """
        if isinstance(kvs, dict):
            field_names = {field.name for field in fields(cls) if field.name in kvs}
            field_values = [kvs.get(n) for n in field_names if kvs.get(n)]
            if not field_values:
                return None
        return _decode_dataclass(cls, kvs, infer_missing)


class CliProcessorConfig(ProcessorConfig, CliMixin):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--reprocess"],
                is_flag=True,
                default=False,
                help="Reprocess a downloaded file even if the relevant structured "
                "output .json file in output directory already exists.",
            ),
            click.Option(
                ["--output-dir"],
                default="structured-output",
                help="Where to place structured output .json files.",
            ),
            click.Option(
                ["--work-dir"],
                type=str,
                default=str(
                    (Path.home() / ".cache" / "unstructured" / "ingest" / "pipeline").resolve(),
                ),
                show_default=True,
                help="Where to place working files when processing each step",
            ),
            click.Option(
                ["--num-processes"],
                default=2,
                show_default=True,
                help="Number of parallel processes with which to process docs",
            ),
            click.Option(
                ["--raise-on-error"],
                is_flag=True,
                default=False,
                help="Is set, will raise error if any doc in the pipeline fail. Otherwise will "
                "log error and continue with other docs",
            ),
            click.Option(["-v", "--verbose"], is_flag=True, default=False),
        ]
        return options


class CliReadConfig(ReadConfig, CliMixin):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--download-dir"],
                help="Where files are downloaded to, defaults to a location at"
                "`$HOME/.cache/unstructured/ingest/<connector name>/<SHA256>`.",
            ),
            click.Option(
                ["--re-download"],
                is_flag=True,
                default=False,
                help="Re-download files even if they are already present in download dir.",
            ),
            click.Option(
                ["--preserve-downloads"],
                is_flag=True,
                default=False,
                help="Preserve downloaded files. Otherwise each file is removed "
                "after being processed successfully.",
            ),
            click.Option(
                ["--download-only"],
                is_flag=True,
                default=False,
                help="Download any files that are not already present in either --download-dir or "
                "the default download ~/.cache/... location in case --download-dir "
                "is not specified and "
                "skip processing them through unstructured.",
            ),
            click.Option(
                ["--max-docs"],
                default=None,
                type=int,
                help="If specified, process at most the specified number of documents.",
            ),
        ]
        return options


class CliPartitionConfig(PartitionConfig, CliMixin):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--pdf-infer-table-structure"],
                is_flag=True,
                default=False,
                help="Partition will include the table's text_as_html " "in the response metadata.",
            ),
            click.Option(
                ["--strategy"],
                default="auto",
                help="The method that will be used to process the documents. "
                "Default: auto. Other strategies include `fast` and `hi_res`.",
            ),
            click.Option(
                ["--ocr-languages"],
                default=None,
                type=DelimitedString(delimiter="+"),
                help="A list of language packs to specify which languages to use for OCR, "
                "separated by '+' e.g. 'eng+deu' to use the English and German language packs. "
                "The appropriate Tesseract "
                "language pack needs to be installed.",
            ),
            click.Option(
                ["--encoding"],
                default=None,
                help="Text encoding to use when reading documents. By default the encoding is "
                "detected automatically.",
            ),
            click.Option(
                ["--skip-infer-table-types"],
                type=DelimitedString(),
                default=None,
                help="Optional list of document types to skip table extraction on",
            ),
            click.Option(
                ["--additional-partition-args"],
                type=Dict(),
                help="A json string representation of values to pass through to partition()",
            ),
            click.Option(
                ["--fields-include"],
                type=DelimitedString(),
                default=["element_id", "text", "type", "metadata", "embeddings"],
                help="Comma-delimited list. If set, include the specified top-level "
                "fields in an element.",
            ),
            click.Option(
                ["--flatten-metadata"],
                is_flag=True,
                default=False,
                help="Results in flattened json elements. "
                "Specifically, the metadata key values are brought to "
                "the top-level of the element, and the `metadata` key itself is removed.",
            ),
            click.Option(
                ["--metadata-include"],
                default=[],
                type=DelimitedString(),
                help="Comma-delimited list. If set, include the specified metadata "
                "fields if they exist and drop all other fields. ",
            ),
            click.Option(
                ["--metadata-exclude"],
                default=[],
                type=DelimitedString(),
                help="Comma-delimited list. If set, drop the specified metadata "
                "fields if they exist.",
            ),
            click.Option(
                ["--partition-by-api"],
                is_flag=True,
                default=False,
                help="Use a remote API to partition the files."
                " Otherwise, use the function from partition.auto",
            ),
            click.Option(
                ["--partition-endpoint"],
                default="https://api.unstructured.io/general/v0/general",
                help="If partitioning via api, use the following host. "
                "Default: https://api.unstructured.io/general/v0/general",
            ),
            click.Option(
                ["--api-key"],
                default=None,
                help="API Key for partition endpoint.",
            ),
            click.Option(
                ["--hi-res-model-name"],
                default=None,
                help="Model name for hi-res strategy.",
            ),
        ]
        return options


class CliRecursiveConfig(CliConfig):
    recursive: bool

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--recursive"],
                is_flag=True,
                default=False,
                help="Recursively download files in their respective folders "
                "otherwise stop at the files in provided folder level.",
            ),
        ]
        return options


class CliFilesStorageConfig(FileStorageConfig, CliMixin):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--remote-url"],
                required=True,
                help="Remote fsspec URL formatted as `protocol://dir/path`",
            ),
            click.Option(
                ["--uncompress"],
                type=bool,
                default=False,
                is_flag=True,
                help="Uncompress any archived files. Currently supporting zip and tar "
                "files based on file extension.",
            ),
            click.Option(
                ["--recursive"],
                is_flag=True,
                default=False,
                help="Recursively download files in their respective folders "
                "otherwise stop at the files in provided folder level.",
            ),
        ]
        return options


class CliEmbeddingConfig(EmbeddingConfig, CliMixin):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        from unstructured.embed import EMBEDDING_PROVIDER_TO_CLASS_MAP

        options = [
            click.Option(
                ["--embedding-provider"],
                help="Type of the embedding class to be used. Can be one of: "
                f"{list(EMBEDDING_PROVIDER_TO_CLASS_MAP)}",
                type=click.Choice(list(EMBEDDING_PROVIDER_TO_CLASS_MAP)),
            ),
            click.Option(
                ["--embedding-api-key"],
                help="API key for the embedding model, for the case an API key is needed.",
                type=str,
                default=None,
            ),
            click.Option(
                ["--embedding-model-name"],
                help="Embedding model name, if needed. "
                "Chooses a particular LLM between different options, to embed with it.",
                type=str,
                default=None,
            ),
        ]
        return options

    @classmethod
    def from_dict(
        cls,
        kvs: Json,
        *,
        infer_missing=False,
    ):
        """
        Extension of the dataclass from_dict() to avoid a naming conflict with other CLI params.
        This allows CLI arguments to be prepended with embedding_ during CLI invocation but
        doesn't require that as part of the field names in this class
        """
        if isinstance(kvs, dict):
            new_kvs = {
                k[len("embedding_") :]: v  # noqa: E203
                for k, v in kvs.items()
                if k.startswith("embedding_")
            }
            if len(new_kvs.keys()) == 0:
                return None
            if not new_kvs.get("provider", None):
                return None
            return _decode_dataclass(cls, new_kvs, infer_missing)
        return _decode_dataclass(cls, kvs, infer_missing)


class CliChunkingConfig(ChunkingConfig, CliMixin):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--chunk-elements"],
                is_flag=True,
                default=False,
            ),
            click.Option(
                ["--chunk-multipage-sections"],
                is_flag=True,
                default=False,
            ),
            click.Option(
                ["--chunk-combine-text-under-n-chars"],
                type=int,
                default=500,
                show_default=True,
            ),
            click.Option(
                ["--chunk-new-after-n-chars"],
                type=int,
                default=1500,
                show_default=True,
            ),
            click.Option(
                ["--chunk-max-characters"],
                type=int,
                default=1500,
                show_default=True,
            ),
        ]
        return options

    @classmethod
    def from_dict(
        cls,
        kvs: Json,
        *,
        infer_missing=False,
    ):
        """
        Extension of the dataclass from_dict() to avoid a naming conflict with other CLI params.
        This allows CLI arguments to be prepended with chunking_ during CLI invocation but
        doesn't require that as part of the field names in this class
        """
        if isinstance(kvs, dict):
            new_kvs = {}
            if "chunk_elements" in kvs:
                chunk_elements = kvs.pop("chunk_elements")
                if not chunk_elements:
                    return None
                new_kvs["chunk_elements"] = chunk_elements
            new_kvs.update(
                {
                    k[len("chunk_") :]: v  # noqa: E203
                    for k, v in kvs.items()
                    if k.startswith("chunk_")
                },
            )
            if len(new_kvs.keys()) == 0:
                return None
            return _decode_dataclass(cls, new_kvs, infer_missing)
        return _decode_dataclass(cls, kvs, infer_missing)


class CliPermissionsConfig(PermissionsConfig, CliMixin):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--permissions-application-id"],
                type=str,
                help="Microsoft Graph API application id",
            ),
            click.Option(
                ["--permissions-client-cred"],
                type=str,
                help="Microsoft Graph API application credentials",
            ),
            click.Option(
                ["--permissions-tenant"],
                type=str,
                help="e.g https://contoso.onmicrosoft.com to get permissions data within tenant.",
            ),
        ]
        return options

    @classmethod
    def from_dict(
        cls,
        kvs: Json,
        *,
        infer_missing=False,
    ):
        """
        Extension of the dataclass from_dict() to avoid a naming conflict with other CLI params.
        This allows CLI arguments to be prepended with permissions_ during CLI invocation but
        doesn't require that as part of the field names in this class. It also checks if the
        CLI params are provided as intended.
        """

        if isinstance(kvs, dict):
            permissions_application_id = kvs.get("permissions_application_id")
            permissions_client_cred = kvs.get("permissions_client_cred")
            permissions_tenant = kvs.get("permissions_tenant")
            permission_values = [
                permissions_application_id,
                permissions_client_cred,
                permissions_tenant,
            ]
            if any(permission_values) and not all(permission_values):
                raise ValueError(
                    "Please provide either none or all of the following optional values:\n"
                    "--permissions-application-id\n"
                    "--permissions-client-cred\n"
                    "--permissions-tenant",
                )

            new_kvs = {
                k[len("permissions_") :]: v  # noqa: E203
                for k, v in kvs.items()
                if k.startswith("permissions_")
            }
            if len(new_kvs.keys()) == 0:
                return None
            return _decode_dataclass(cls, new_kvs, infer_missing)
        return _decode_dataclass(cls, kvs, infer_missing)
