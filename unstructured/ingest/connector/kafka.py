import base64
import itertools
import json
import socket
import typing as t
from dataclasses import dataclass
from pathlib import Path

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError, SourceConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    BaseSingleIngestDoc,
    BaseSourceConnector,
    ConfigSessionHandleMixin,
    IngestDocCleanupMixin,
    IngestDocSessionHandleMixin,
    ReadConfig,
    SourceConnectorCleanupMixin,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from confluent_kafka import Consumer, Producer


@dataclass
class KafkaAccessConfig(AccessConfig):
    kafka_api_key: t.Optional[str] = enhanced_field(sensitive=True)
    secret: t.Optional[str] = enhanced_field(sensitive=True)


@dataclass
class SimpleKafkaConfig(ConfigSessionHandleMixin, BaseConnectorConfig):
    bootstrap_server: str
    port: str
    topic: str
    access_config: KafkaAccessConfig
    confluent: t.Optional[bool] = True
    num_messages_to_consume: t.Optional[int] = 1


@dataclass
class KafkaWriteConfig(WriteConfig):
    batch_size: int = 50
    num_processes: int = 1


@dataclass
class KafkaReadConfig(ReadConfig):
    pass


@dataclass
class KafkaDestinationConnector(IngestDocSessionHandleMixin, BaseDestinationConnector):
    """Connector to write BaseIngestDoc types to Kafka
    Writes messages to Kafka in the format:
    "type"<type>
    "text":<the partitioned text>
    "filename":<name of the upstream file>
    """

    write_config: KafkaWriteConfig
    connector_config: SimpleKafkaConfig
    _producer: t.Optional["Producer"] = None

    @property
    def kafka_producer(self):
        if self._producer is None:
            self._producer = self.create_producer()
        return self._producer

    def initialize(self):
        pass

    @requires_dependencies(["confluent_kafka"], extras="kafka")
    def create_producer(self) -> "Producer":
        from confluent_kafka import Producer

        is_confluent = self.connector_config.confluent
        bootstrap = self.connector_config.bootstrap_server
        port = self.connector_config.port

        conf = {
            "bootstrap.servers": f'{bootstrap}:{port}',
            "client.id": socket.gethostname(),
        }

        if is_confluent:
            api_key = self.connector_config.access_config.kafka_api_key
            secret = self.connector_config.access_config.secret
            conf["sasl.mechanism"] = "PLAIN"
            conf["security.protocol"] = "SASL_SSL"
            conf["sasl.username"] = api_key
            conf["sasl.password"] = secret

        producer = Producer(conf)
        logger.debug(f"Connected to bootstrap: {bootstrap}")
        return producer

    @DestinationConnectionError.wrap
    def check_connection(self):
        _ = self.kafka_producer

    @staticmethod
    def chunks(iterable, batch_size=100):
        """A helper function to break an iterable into chunks of size batch_size."""
        it = iter(iterable)
        chunk = tuple(itertools.islice(it, batch_size))
        while chunk:
            yield chunk
            chunk = tuple(itertools.islice(it, batch_size))

    @DestinationConnectionError.wrap
    def upload_msg(self, batch) -> int:
        logger.debug(f"Uploding batch: {batch}")
        topic = self.connector_config.topic
        producer = self.kafka_producer
        uploaded = 0
        for i in range(len(batch)):
            filename = f'{batch[i].pop("filename")}'
            producer.produce(topic, key=filename, value=str(batch[i]))
            uploaded += 1
        return uploaded

    @DestinationConnectionError.wrap
    def write_dict(self, *args, dict_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(f"Writing {len(dict_list)} documents to Kafka")
        BATCH_SIZE = 4
        num_uploaded = 0

        """
        if self.write_config.num_processes == 1:
           #self.upload_msg("asdf")
           for chunk in self.chunks(dict_list, BATCH_SIZE):
                num_uploaded += self.upload_msg(chunk)  # noqa: E203
        else:
            with mp.Pool(processes=self.write_config.num_processes) as pool:
                pool.map(self.upload_msg, list(self.chunks(dict_list, BATCH_SIZE)))
        """
        for chunk in self.chunks(dict_list, BATCH_SIZE):
            num_uploaded += self.upload_msg(chunk)  # noqa: E203

        producer = self.kafka_producer
        producer.flush()
        logger.info(f"Uploaded {num_uploaded} documents to Kafka")

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        content_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                dict_content = json.load(json_file)
                for content in dict_content:
                    content_list.append(
                        {
                            "type": content["type"],
                            "text": content["text"],
                            "filename": content["metadata"]["filename"],
                        }
                    )
        self.write_dict(dict_list=content_list)


@dataclass
class KafkaIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    """Class encapsulating fetching a message and writing processed results."""

    connector_config: SimpleKafkaConfig
    raw_content: str
    raw_filename: str
    registry_name: str = "kafka"

    def _tmp_download_file(self):
        # topic_file = self.connector_config.topic + "-" + self.raw_filename + ".json"
        topic_file = self.connector_config.topic + "-" + self.raw_filename 
        return Path(self.read_config.download_dir) / topic_file

    @property
    def version(self) -> t.Optional[str]:
        return None

    @property
    def source_url(self) -> t.Optional[str]:
        return None

    @property
    def filename(self):
        """The filename of the file created"""
        return self._tmp_download_file()

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @property
    def _output_filename(self):
        """Create filename document id combined with a hash of the query to uniquely identify
        the output file."""
        print("###### ******** ADDING JSON &&&&&&")
        output_file = self.connector_config.topic + ".json"
        return Path(self.processor_config.output_dir) / output_file

    @SourceConnectionError.wrap
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        self._create_full_tmp_dir_path()

        pdf_data = base64.b64decode(self.raw_content)

        with open(self.filename, "wb") as file:
            file.write(pdf_data)


@dataclass
class KafkaSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Source connector for Kafka.
    Main job is to consume from a Kafka topic and create instances of
    KakfaIngestDoc.
    Note that messages have the format of:
    <filename>: the name of the file (with correct file extension)
    <content>: base64 encoded (whether was binary or not)
    """

    connector_config: SimpleKafkaConfig
    _consumer: t.Optional["Consumer"] = None

    def check_connection(self):
        pass


    def initialize(self):
        topic = self.connector_config.topic
        logger.info(f"Subscribing to topic: {topic}")
        self.kafka_consumer.subscribe([topic])

    @property
    def kafka_consumer(self):
        if self._consumer is None:
            self._consumer = self.create_consumer()
        return self._consumer

    @requires_dependencies(["confluent_kafka"], extras="kafka")
    def create_consumer(self) -> "Consumer":
        from confluent_kafka import Consumer

        is_confluent = self.connector_config.confluent
        bootstrap = self.connector_config.bootstrap_server
        port = self.connector_config.port

        conf = {
            "bootstrap.servers": f'{bootstrap}:{port}',
            "client.id": socket.gethostname(),
            "group.id": "your_group_id",
            "enable.auto.commit": "false",
            "auto.offset.reset": "earliest",
            "message.max.bytes": 10485760,
        }

        if is_confluent:
            kafka_api_key = self.connector_config.access_config.kafka_api_key
            secret = self.connector_config.access_config.secret
            conf["sasl.mechanism"] = "PLAIN"
            conf["security.protocol"] = "SASL_SSL"
            conf["sasl.username"] = kafka_api_key
            conf["sasl.password"] = secret

        consumer = Consumer(conf)
        logger.debug(f"Kafka Consumer connected to bootstrap: {bootstrap}")
        return consumer

    @SourceConnectionError.wrap
    def get_ingest_docs(self):
        from confluent_kafka import KafkaError

        consumer = self.kafka_consumer
        running = True

        collected = []
        num_messages_to_consume = self.connector_config.num_messages_to_consume
        logger.info(f"Config set for blocking on {num_messages_to_consume} messages")
        # Consume specified number of messages
        while running:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                logger.debug("No Kafka messages found")
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    logger.error(
                        "%% %s [%d] reached end at offset %d\n"
                        % (msg.topic(), msg.partition(), msg.offset())
                    )
            else:
                collected.append(json.loads(msg.value().decode("utf8")))
                if len(collected) >= num_messages_to_consume:
                    logger.debug(f"Found {len(collected)} messages, stopping")
                    running = False
                    consumer.commit(asynchronous=False)
                    break

        return [
            KafkaIngestDoc(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                raw_filename=msg["filename"],
                raw_content=msg["content"],
            )
            for msg in collected
        ]