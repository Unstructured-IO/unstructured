import json

CLUSTER_URL = "http://localhost:9200"
INDEX_NAME = "ingest-test-destination"
USER = "admin"
PASSWORD = "admin"
MAPPING_PATH = "docs/source/ingest/destination_connectors/data/opensearch_elements_mappings.json"

with open(MAPPING_PATH) as f:
    mappings = json.load(f)
