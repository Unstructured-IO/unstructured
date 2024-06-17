import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import CliConfig
from unstructured.ingest.connector.kafka import KafkaWriteConfig, SimpleKafkaConfig

CMD_NAME = "kafka"


@dataclass
class KafkaCliConfig(SimpleKafkaConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--bootstrap-server"], required=True, type=str, help="Broker server hostname"
            ),
            click.Option(
                ["--port"],
                required=True,
                type=str,
                help="The bootstrap port",
            ),
            click.Option(
                ["--topic"],
                required=True,
                type=str,
                help="The topic to write into.'",
            ),
            click.Option(
                ["--kafka-api-key"],
                required=False,
                type=str,
                help="The API KEY",
            ),
            click.Option(
                ["--secret"],
                required=False,
                type=str,
                help="The secret",
            ),
            click.Option(
                ["--num-messages-to-consume"],
                required=False,
                type=int,
                default=1,
                help="The number of messages to consume before unblocking the consumer",
            ),
            click.Option(
                ["--timeout"],
                required=False,
                type=float,
                default=1.0,
                help="Maximum time to block waiting for message(Seconds)",
            ),
            click.Option(
                ["--confluent"],
                required=False,
                type=bool,
                default=True,
                help="Whether this Kafka instance is from Confluent",
            ),
        ]
        return options


@dataclass
class KafkaCliWriteConfig(KafkaWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=4,
                type=int,
                help="Number of records per batch",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name=CMD_NAME,
        cli_config=KafkaCliConfig,
    )
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=KafkaCliConfig,
        additional_cli_options=[KafkaCliWriteConfig],
        write_config=KafkaWriteConfig,
    )
    return cmd_cls
