import argparse
import json
import uuid
from dataclasses import dataclass
from datetime import timedelta

from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions


@dataclass
class ClusterConfig:
    username: str
    password: str
    connection_string: str
    bucket_name: str
    scope_name: str
    collection_name: str


def get_client(cluster_config: ClusterConfig) -> Cluster:
    auth = PasswordAuthenticator(cluster_config.username, cluster_config.password)
    options = ClusterOptions(auth)
    options.apply_profile("wan_development")
    cluster = Cluster(cluster_config.connection_string, options)
    cluster.wait_until_ready(timedelta(seconds=5))
    return cluster


def setup_cluster(cluster_config: ClusterConfig, source_file: str):
    cluster = get_client(cluster_config)
    bucket = cluster.bucket(cluster_config.bucket_name)
    scope = bucket.scope(cluster_config.scope_name)
    collection = scope.collection(cluster_config.collection_name)

    cluster.query(
        "Create primary index on `{}`.`{}`.`{}`".format(
            cluster_config.bucket_name, cluster_config.scope_name, cluster_config.collection_name
        )
    )

    with open(source_file) as file:
        for line in file:
            try:
                doc = json.loads(line)
                # Assuming 'cbmid' is the document ID. Adjust as necessary.
                doc_id = doc.get("cbmid", uuid.uuid4())
                if doc_id:
                    collection.upsert(doc_id, doc)
                else:
                    print("Document ID not found in the line, skipping upsert.")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                raise RuntimeError(f"Error decoding JSON: {e}")
            except Exception as e:
                print(f"Error upserting document: {e}")
                raise RuntimeError(f"Error upserting document: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Couchbase cluster and create search index.")
    parser.add_argument("--username", required=True, help="Couchbase username")
    parser.add_argument("--password", required=True, help="Couchbase password")
    parser.add_argument("--connection_string", required=True, help="Couchbase connection string")
    parser.add_argument("--bucket_name", required=True, help="Couchbase bucket name")
    parser.add_argument("--scope_name", required=True, help="Couchbase scope name")
    parser.add_argument("--collection_name", required=True, help="Couchbase collection name")
    parser.add_argument("--source_file", required=True, help="Source file to ingest")

    args = parser.parse_args()

    config = ClusterConfig(
        username=args.username,
        password=args.password,
        connection_string=args.connection_string,
        bucket_name=args.bucket_name,
        scope_name=args.scope_name,
        collection_name=args.collection_name,
    )

    setup_cluster(config, args.source_file)
