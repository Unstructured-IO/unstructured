# type: ignore[import]
"""Helper module for setting up and interacting with a Couchbase cluster."""

import argparse
import json
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlparse

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
    print(cluster_config)
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

    # # Create Search Index
    # search_index = SearchIndex(
    #     name=search_index_name,
    #     source_type="couchbase",
    #     idx_type="fulltext-index",
    #     source_name=bucket_name,
    #     params={
    #         "doc_config": {
    #             "docid_prefix_delim": "",
    #             "docid_regexp": "",
    #             "mode": "scope.collection.type_field",
    #             "type_field": "type"
    #         },
    #         "mapping": {
    #             "analysis": {},
    #             "default_analyzer": "standard",
    #             "default_datetime_parser": "dateTimeOptional",
    #             "default_field": "_all",
    #             "default_mapping": {
    #                 "dynamic": False,
    #                 "enabled": False
    #             },
    #             "default_type": "_default",
    #             "docvalues_dynamic": False,
    #             "index_dynamic": False,
    #             "store_dynamic": True,
    #             "type_field": "_type",
    #             "types": {
    #                 f"{scope_name}.{collection_name}": {
    #                     "dynamic": False,
    #                     "enabled": True,
    #                     "properties": {
    #                         "embedding": {
    #                             "dynamic": False,
    #                             "enabled": True,
    #                             "fields": [
    #                                 {
    #                                     "dims": 384,
    #                                     "index": True,
    #                                     "name": "embedding",
    #                                     "similarity": "l2_norm",
    #                                     "type": "vector",
    #                                     "vector_index_optimized_for": "recall"
    #                                 }
    #                             ]
    #                         },
    #                         "metadata": {
    #                             "dynamic": True,
    #                             "enabled": True
    #                         },
    #                         "text": {
    #                             "dynamic": False,
    #                             "enabled": True,
    #                             "fields": [
    #                                 {
    #                                     "analyzer": "keyword",
    #                                     "include_term_vectors": True,
    #                                     "index": True,
    #                                     "name": "text",
    #                                     "store": True,
    #                                     "type": "text"
    #                                 }
    #                             ]
    #                         }
    #                     }
    #                 }
    #             }
    #         },
    #         "store": {
    #             "indexType": "scorch",
    #             "segmentVersion": 16
    #         }
    #     }
    # )

    # scope.search_indexes().upsert_index(search_index)

    # Create Search Index using REST API

    # Parse the connection string to extract the host and port
    parsed_url = urlparse(config.connection_string)
    print("parsed url")

    is_secure = parsed_url.scheme == "couchbases"
    host = parsed_url.hostname
    port = 18094 if is_secure else 8094
    scheme = "https" if is_secure else "http"

    url = (
        f"{scheme}://{host}:{port}/api/bucket/{cluster_config.bucket_name}"
        f"/scope/{cluster_config.scope_name}"
        f"/index/{cluster_config.search_index_name}"
    )
    print("url is", url)

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
    scope_index_manager.upsert_index(SearchIndex.from_json(json.dumps(index_definition)))


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
