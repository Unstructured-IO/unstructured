import os

from unstructured.ingest.connector.local import SimpleLocalConfig
from unstructured.ingest.connector.pinecone import (
    PineconeAccessConfig,
    PineconeWriteConfig,
    SimplePineconeConfig,
    PineconeDestinationConnector,
)
from unstructured.ingest.interfaces import (
    ChunkingConfig,
    EmbeddingConfig,
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import LocalRunner
from unstructured.ingest.runner.writers.base_writer import Writer
from unstructured.ingest.runner.writers.pinecone import (
    PineconeWriter,
)
import random
import requests

RANDOM_INDEX = f"test-connect-{random.randint(0, 1000)}" 
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENVIRONMENT="us-east1-gcp"

def set_up_pinecone_index():
    url = f"https://controller.{PINECONE_ENVIRONMENT}.pinecone.io/databases"
    headers = {
      "accept": "text/plain",
      "content-type": "application/json",
      "Api-Key": PINECONE_API_KEY
    }
    data = {
      "name": RANDOM_INDEX,
      "dimension": 384,
      "metric": "cosine",
      "pods": 1,
      "pod_type": "p1.x1"
    }

    response = requests.post(url, headers=headers, json=data)
    response_code = response.status_code
    print(response_code)

def get_writer() -> Writer:
    return PineconeWriter(
        connector_config=SimplePineconeConfig(
            access_config=PineconeAccessConfig(api_key=os.getenv("PINECONE_API_KEY")),
            index_name=RANDOM_INDEX,
            environment=PINECONE_ENVIRONMENT,
        ),
        write_config=PineconeWriteConfig(batch_size=80),

    )
def get_dest():
    writer=get_writer(),
    return PineconeDestinationConnector(
        write_config=writer[0].write_config,
        connector_config=writer[0].connector_config,
    )


def test_pinecone_connection():
    writer = get_writer()
    dest = get_dest()
    # breakpoint()
    check=dest.check_connection()
    
    breakpoint()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-pinecone",
            num_processes=1,
        ),
        connector_config=SimpleLocalConfig(
            input_path="example-docs/book-war-and-peace-1225p.txt",
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        chunking_config=ChunkingConfig(chunk_elements=True),
        embedding_config=EmbeddingConfig(
            provider="langchain-huggingface",
        ),
        writer=writer,
        writer_kwargs={},
    )
    breakpoint()
    print("hi")
    # runner.run()
    

