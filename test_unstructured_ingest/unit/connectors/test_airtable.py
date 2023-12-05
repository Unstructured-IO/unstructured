import json

from unstructured.ingest.connector.airtable import SimpleAirtableConfig
from unstructured.ingest.cli.utils import extract_config

def test_create_airtable_config():
    click_options = {
        "list_of_paths": ["this", "is", "a", "path"],
        "personal_access_token": "TOKEN"
    }
    config = extract_config(flat_data=click_options, config=SimpleAirtableConfig)
    expected_dict = {"access_config": {"personal_access_token": "TOKEN"}, "list_of_paths": "['this', 'is', 'a', 'path']"}
    assert config.to_json(sort_keys=True) == json.dumps(expected_dict, sort_keys=True)
    assert config.to_dict() == expected_dict