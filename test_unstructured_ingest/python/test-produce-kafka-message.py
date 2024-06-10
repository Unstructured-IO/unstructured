#!/usr/bin/env python
import base64
import json
import socket

import click
from confluent_kafka import Producer


@click.group(name="kafka-ingest")
def cli():
    pass


@cli.command()
@click.option("--input-file", type=str, required=True)
@click.option("--bootstrap-server", type=str, required=True)
@click.option("--topic", type=str, required=True)
@click.option("--api-key", type=str, required=False)
@click.option("--secret", type=str, required=False)
@click.option("--confluent", type=bool, required=False, default=True)
@click.option("--port", type=int, required=False, default=9092)
def up(
    input_file: str,
    bootstrap_server: str,
    topic: str,
    api_key: str,
    secret: str,
    confluent: bool,
    port: int,
):
    conf = {
        "bootstrap.servers": f"{bootstrap_server}:{port}",
        "client.id": socket.gethostname(),
        "message.max.bytes": 10485760,
    }

    print(f"Confluent setting: {confluent}")
    if confluent:
        conf["security.protocol"] = "SASL_SSL"
        conf["sasl.mechanism"] = "PLAIN"
        conf["sasl.username"] = api_key
        conf["sasl.password"] = secret

    producer = Producer(conf)

    # Read the file in binary mode and encode content in base64
    with open(input_file, "rb") as file:
        file_content = base64.b64encode(file.read()).decode("utf-8")

    print(f"Message is {len(file_content)} bytes long")
    # Construct the message with filename and file content
    message = json.dumps({"filename": input_file.split("/")[-1], "content": file_content}).encode(
        "utf-8"
    )

    # Send the message to Kafka
    producer.produce(topic, message)
    producer.flush()
    print(f"File and filename sent to Kafka topic {topic} successfully.")


if __name__ == "__main__":
    cli()
