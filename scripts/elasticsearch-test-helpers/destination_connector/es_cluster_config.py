import json
import os

CLUSTER_URL = "http://localhost:9200"
INDEX_NAME = "ingest-test-destination"
USER = os.environ["ELASTICSEARCH_USER"]
PASSWORD = os.environ["ELASTICSEARCH_PASSWORD"]
MAPPING_PATH = "docs/source/ingest/destination_connectors/elasticsearch_elements_mappings.json"

with open(MAPPING_PATH) as f:
    mappings = json.load(f)
