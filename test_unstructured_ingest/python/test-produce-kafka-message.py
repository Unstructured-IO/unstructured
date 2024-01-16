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
@click.option("--api-key", type=str, required=True)
@click.option("--secret", type=str, required=True)
def up(input_file: str, bootstrap_server: str, topic: str, api_key: str, secret: str):
    conf = {
        "bootstrap.servers": bootstrap_server,
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.username": api_key,
        "sasl.password": secret,
        "client.id": socket.gethostname(),
        "message.max.bytes": 10485760,
    }
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
