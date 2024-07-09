# type: ignore[import]
"""Helper module for setting up and interacting with a Couchbase cluster."""

import argparse
import json
import time
from dataclasses import dataclass
from datetime import timedelta

from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.management.search import SearchIndex
from couchbase.options import ClusterOptions


@dataclass
class ClusterConfig:
    username: str
    password: str
    connection_string: str
    bucket_name: str
    scope_name: str
    collection_name: str
    search_index_name: str


def get_client(cluster_config: ClusterConfig) -> Cluster:
    auth = PasswordAuthenticator(cluster_config.username, cluster_config.password)
    options = ClusterOptions(auth)
    options.apply_profile("wan_development")
    cluster = Cluster(cluster_config.connection_string, options)
    cluster.wait_until_ready(timedelta(seconds=5))
    return cluster


def setup_cluster(cluster_config: ClusterConfig):
    cluster = get_client(cluster_config)
    bucket = cluster.bucket(cluster_config.bucket_name)
    scope = bucket.scope(cluster_config.scope_name)

    # Create Primary Index
    cluster.query(
        "Create primary index on `{}`.`{}`.`{}`".format(
            cluster_config.bucket_name, cluster_config.scope_name, cluster_config.collection_name
        )
    )

    index_definition = {
        "type": "fulltext-index",
        "name": config.search_index_name,
        "sourceType": "couchbase",
        "sourceName": config.bucket_name,
        "planParams": {"maxPartitionsPerPIndex": 1024, "indexPartitions": 1},
        "params": {
            "doc_config": {
                "docid_prefix_delim": "",
                "docid_regexp": "",
                "mode": "scope.collection.type_field",
                "type_field": "type",
            },
            "mapping": {
                "analysis": {},
                "default_analyzer": "standard",
                "default_datetime_parser": "dateTimeOptional",
                "default_field": "_all",
                "default_mapping": {"dynamic": True, "enabled": False},
                "default_type": "_default",
                "docvalues_dynamic": False,
                "index_dynamic": True,
                "store_dynamic": True,
                "type_field": "_type",
                "types": {
                    f"{config.scope_name}.{config.collection_name}": {
                        "dynamic": False,
                        "enabled": True,
                        "properties": {
                            "embedding": {
                                "dynamic": False,
                                "enabled": True,
                                "fields": [
                                    {
                                        "dims": 384,
                                        "index": True,
                                        "name": "embedding",
                                        "similarity": "dot_product",
                                        "type": "vector",
                                        "vector_index_optimized_for": "recall",
                                    }
                                ],
                            },
                            "metadata": {"dynamic": True, "enabled": True},
                            "text": {
                                "dynamic": False,
                                "enabled": True,
                                "fields": [
                                    {
                                        "include_in_all": True,
                                        "index": True,
                                        "name": "text",
                                        "store": True,
                                        "type": "text",
                                    }
                                ],
                            },
                        },
                    }
                },
            },
            "store": {"indexType": "scorch", "segmentVersion": 16},
        },
        "sourceParams": {},
    }

    scope_index_manager = scope.search_indexes()
    search_index_def = SearchIndex.from_json(json.dumps(index_definition))
    max_attempts = 20
    attempt = 0
    while attempt < max_attempts:
        try:
            scope_index_manager.upsert_index(search_index_def)
            break
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_attempts}: Error creating search index: {e}")
            time.sleep(3)
            attempt += 1

    if attempt == max_attempts:
        print(f"Error creating search index after {max_attempts} attempts.")
        raise RuntimeError(f"Error creating search index after {max_attempts} attempts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Couchbase cluster and create search index.")
    parser.add_argument("--username", required=True, help="Couchbase username")
    parser.add_argument("--password", required=True, help="Couchbase password")
    parser.add_argument("--connection_string", required=True, help="Couchbase connection string")
    parser.add_argument("--bucket_name", required=True, help="Couchbase bucket name")
    parser.add_argument("--scope_name", required=True, help="Couchbase scope name")
    parser.add_argument("--collection_name", required=True, help="Couchbase collection name")
    parser.add_argument("--search_index_name", required=True, help="Couchbase search index name")

    args = parser.parse_args()

    config = ClusterConfig(
        username=args.username,
        password=args.password,
        connection_string=args.connection_string,
        bucket_name=args.bucket_name,
        scope_name=args.scope_name,
        collection_name=args.collection_name,
        search_index_name=args.search_index_name,
    )

    setup_cluster(config)
