from dataclasses import dataclass
from typing import Any

import click
from dataclasses_json.core import Json

from unstructured.embed import EMBEDDING_PROVIDER_TO_CLASS_MAP
from unstructured.ingest.v2.cli.interfaces import CliConfig


@dataclass
class EmbedderCliConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
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
            click.Option(
                ["--embedding-aws-access-key-id"],
                help="AWS access key used for AWS-based embedders, such as bedrock",
                type=str,
                default=None,
            ),
            click.Option(
                ["--embedding-aws-secret-access-key"],
                help="AWS secret key used for AWS-based embedders, such as bedrock",
                type=str,
                default=None,
            ),
            click.Option(
                ["--embedding-aws-region"],
                help="AWS region used for AWS-based embedders, such as bedrock",
                type=str,
                default="us-west-2",
            ),
        ]
        return options

    @classmethod
    def from_dict(cls, kvs: Json, **kwargs: Any):
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
            if not new_kvs.get("provider"):
                return None
            return super().from_dict(new_kvs, **kwargs)
        return super().from_dict(kvs, **kwargs)
