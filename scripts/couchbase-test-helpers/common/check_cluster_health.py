import argparse
import time
from dataclasses import dataclass

import requests
import urllib3


@dataclass
class ClusterConfig:
    username: str
    password: str
    connection_string: str
    bucket_name: str


def check_bucket_health(cluster_config: ClusterConfig, url: str):
    max_attempts = 20
    attempt = 0

    while attempt < max_attempts:
        response = requests.get(
            url, auth=(cluster_config.username, cluster_config.password), verify=False
        )
        response_data = response.json()
        if (
            response.status_code == 200
            and "nodes" in response_data
            and len(response_data["nodes"]) > 0
            and response_data["nodes"][0]["status"] == "healthy"
        ):
            print(f"Bucket '{cluster_config.bucket_name}' is healthy.")
            break
        else:
            print(
                f"Attempt {attempt + 1}/{max_attempts}: "
                f"Bucket '{cluster_config.bucket_name}' health check failed"
            )
            time.sleep(3)  # Wait for 1 second before the next attempt
            attempt += 1

    if attempt == max_attempts:
        print(
            f"Bucket '{cluster_config.bucket_name}'"
            f" health check failed after {max_attempts} attempts."
        )
        raise RuntimeError(
            f"Bucket '{cluster_config.bucket_name}'"
            f" health check failed after {max_attempts} attempts."
        )


def check_fts_service_health(cluster_config: ClusterConfig, url: str):
    max_attempts = 20
    attempt = 0

    while attempt < max_attempts:
        response = requests.get(
            url, auth=(cluster_config.username, cluster_config.password), verify=False
        )
        if response.status_code == 200:
            print("FTS service is healthy.")
            break
        else:
            print(f"Attempt {attempt + 1}: FTS service health check failed")
            time.sleep(3)
            attempt += 1

    if attempt == max_attempts:
        print(f"FTS service health check failed after {max_attempts} attempts.")
        raise RuntimeError(f"FTS service health check failed after {max_attempts} attempts.")


def check_health(cluster_config: ClusterConfig):
    host = urllib3.util.parse_url(cluster_config.connection_string).host

    check_bucket_health(
        cluster_config,
        url=f"http://{host}:{8091}/pools/default/buckets/{cluster_config.bucket_name}",
    )

    check_fts_service_health(cluster_config, url=f"http://{host}:{8094}/api/index")

    print("Cluster is healthy")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Couchbase cluster and create search index.")
    parser.add_argument("--username", required=True, help="Couchbase username")
    parser.add_argument("--password", required=True, help="Couchbase password")
    parser.add_argument("--connection_string", required=True, help="Couchbase connection string")
    parser.add_argument("--bucket_name", required=True, help="Couchbase bucket name")

    args = parser.parse_args()

    config = ClusterConfig(
        username=args.username,
        password=args.password,
        connection_string=args.connection_string,
        bucket_name=args.bucket_name,
    )

    check_health(config)
