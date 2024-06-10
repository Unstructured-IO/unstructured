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
    print(f"Getting the number of messages in the topic {topic_name}")
    topic = consumer.list_topics(topic=topic_name)
    print(f'topic {topic}')
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
@click.option("--api-key", type=str, required=False)
@click.option("--secret", type=str, required=False)
@click.option("--confluent", type=bool, required=True, default=True)
@click.option("--port", type=int, required=False, default=9092)
def check(bootstrap_server: str, topic: str, api_key: str, secret: str, confluent:bool, port:int):
    conf = {
        "bootstrap.servers": f'{bootstrap_server}:{port}',
        "client.id": socket.gethostname(),
        "group.id": "your_group_id",
        "enable.auto.commit": "true",
        "auto.offset.reset": "earliest",
    }

    if confluent:
        conf["security.protocol"] = "SASL_SSL"
        conf["sasl.mechanism"] = "PLAIN"
        conf["sasl.username"] = api_key
        conf["sasl.password"] = secret

    consumer = Consumer(conf)
    print("Checking the number of messages in the topic")
    topic_size = get_topic_size(consumer, topic)
    expected = 16
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