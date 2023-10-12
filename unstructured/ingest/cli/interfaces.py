import typing as t
from abc import abstractmethod
from gettext import ngettext
from pathlib import Path

import click
from dataclasses_json.core import Json, _decode_dataclass

from unstructured.ingest.interfaces import (
    BaseConfig,
    ChunkingConfig,
    EmbeddingConfig,
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
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
    def add_cli_options(cmd: click.Command) -> None:
        pass


class CliProcessorConfig(ProcessorConfig, CliMixin):
    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
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
            click.Option(["-v", "--verbose"], is_flag=True, default=False),
        ]
        cmd.params.extend(options)


class CliReadConfig(ReadConfig, CliMixin):
    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
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
        cmd.params.extend(options)


class CliPartitionConfig(PartitionConfig, CliMixin):
    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--skip-infer-table-types"],
                type=DelimitedString(),
                default=None,
                help="Optional list of document types to skip table extraction on",
            ),
            click.Option(
                ["--pdf-infer-table-structure"],
                default=False,
                help="If set to True, partition will include the table's text "
                "content in the response.",
            ),
            click.Option(
                ["--strategy"],
                default="auto",
                help="The method that will be used to process the documents. "
                "Default: auto. Other strategies include `fast` and `hi_res`.",
            ),
            click.Option(
                ["--ocr-languages"],
                default="eng",
                help="A list of language packs to specify which languages to use for OCR, "
                "separated by '+' e.g. 'eng+deu' to use the English and German language packs. "
                "The appropriate Tesseract "
                "language pack needs to be installed."
                "Default: eng",
            ),
            click.Option(
                ["--encoding"],
                default=None,
                help="Text encoding to use when reading documents. By default the encoding is "
                "detected automatically.",
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
        ]
        cmd.params.extend(options)


class CliRecursiveConfig(BaseConfig, CliMixin):
    recursive: bool

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--recursive"],
                is_flag=True,
                default=False,
                help="Recursively download files in their respective folders "
                "otherwise stop at the files in provided folder level.",
            ),
        ]
        cmd.params.extend(options)


class CliRemoteUrlConfig(BaseConfig, CliMixin):
    remote_url: str

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--remote-url"],
                required=True,
                help="Remote fsspec URL formatted as `protocol://dir/path`",
            ),
        ]
        cmd.params.extend(options)


class CliEmbeddingConfig(EmbeddingConfig, CliMixin):
    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--embedding-api-key"],
                help="openai api key",
            ),
            click.Option(
                ["--embedding-model-name"],
                type=str,
                default=None,
            ),
        ]
        cmd.params.extend(options)

    @classmethod
    def from_dict(
        cls,
        kvs: Json,
        *,
        infer_missing=False,
    ):
        """
        Extension of the dataclass from_dict() to avoid a naming conflict with other CLI params.
        This allows CLI arguments to be prepended with chunk_ during CLI invocation but
        doesn't require that as part of the field names in this class
        """
        if isinstance(kvs, dict):
            new_kvs = {
                k[len("embedding-") :]: v  # noqa: E203
                for k, v in kvs.items()
                if k.startswith("embedding_")
            }
            if len(new_kvs.keys()) == 0:
                return None
            if not new_kvs.get("api_key", None):
                return None
            return _decode_dataclass(cls, new_kvs, infer_missing)
        return _decode_dataclass(cls, kvs, infer_missing)


class CliChunkingConfig(ChunkingConfig, CliMixin):
    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
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
                ["--chunk-combine-under-n-chars"],
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
        ]
        cmd.params.extend(options)

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
                    k[len("chunking_") :]: v  # noqa: E203
                    for k, v in kvs.items()
                    if k.startswith("chunking_")
                },
            )
            if len(new_kvs.keys()) == 0:
                return None
            return _decode_dataclass(cls, new_kvs, infer_missing)
        return _decode_dataclass(cls, kvs, infer_missing)
