import json
import os

CLUSTER_URL = "http://localhost:9200"
INDEX_NAME = "ingest-test-destination"
USER = os.environ["ELASTIC_USER"]
PASSWORD = os.environ["ELASTIC_PASSWORD"]
MAPPING_PATH = (
    "scripts/elasticsearch-test-helpers/destination_connector/elasticsearch_elements_mappings.json"
)

with open(MAPPING_PATH) as f:
    mappings = json.load(f)
