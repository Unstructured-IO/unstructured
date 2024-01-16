#!/usr/bin/env python
import socket
from concurrent.futures import ThreadPoolExecutor

import click
from confluent_kafka import Consumer, TopicPartition


@click.group(name="kafka-ingest")
def cli():
    pass


def get_partition_size(consumer: Consumer, topic_name: str, partition_key: int):
    topic_partition = TopicPartition(topic_name, partition_key)
    low_offset, high_offset = consumer.get_watermark_offsets(topic_partition)
    partition_size = high_offset - low_offset
    return partition_size


def get_topic_size(consumer: Consumer, topic_name: str):
    topic = consumer.list_topics(topic=topic_name)
    partitions = topic.topics[topic_name].partitions
    workers, max_workers = [], len(partitions) or 1

    with ThreadPoolExecutor(max_workers=max_workers) as e:
        for partition_key in list(topic.topics[topic_name].partitions.keys()):
            job = e.submit(get_partition_size, consumer, topic_name, partition_key)
            workers.append(job)

    topic_size = sum([w.result() for w in workers])
    return topic_size


@cli.command()
@click.option("--bootstrap-server", type=str, required=True)
@click.option("--topic", type=str, required=True)
@click.option("--api-key", type=str, required=True)
@click.option("--secret", type=str, required=True)
def check(bootstrap_server: str, topic: str, api_key: str, secret: str):
    conf = {
        "bootstrap.servers": bootstrap_server,
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.username": api_key,
        "sasl.password": secret,
        "client.id": socket.gethostname(),
        "group.id": "your_group_id",
        "enable.auto.commit": "false",
        "auto.offset.reset": "earliest",
    }
    consumer = Consumer(conf)
    topic_size = get_topic_size(consumer, topic)
    expected = 37
    print(
        f"Checking that the number of messages found ({topic_size}) "
        f"matches what's expected: {expected}"
    )
    assert (
        topic_size == expected
    ), f"number of messages found ({topic_size}) doesn't match what's expected: {expected}"
    print("successfully checked the number of messages!")


if __name__ == "__main__":
    cli()
