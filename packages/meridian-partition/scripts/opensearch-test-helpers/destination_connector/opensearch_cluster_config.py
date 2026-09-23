import json

CLUSTER_URL = "http://localhost:9247"
INDEX_NAME = "ingest-test-destination"
USER = "admin"
PASSWORD = "admin"
MAPPING_PATH = (
    "scripts/opensearch-test-helpers/destination_connector/opensearch_elements_mappings.json"
)

with open(MAPPING_PATH) as f:
    mappings = json.load(f)
