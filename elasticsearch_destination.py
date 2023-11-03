#!/usr/bin/env python
# Licensed to Elasticsearch B.V under one or more agreements.
# Elasticsearch B.V licenses this file to you under the Apache 2.0 License.
# See the LICENSE file in the project root for more information

"""Script that downloads a public dataset and streams it to an Elasticsearch cluster"""

import csv
from os.path import abspath, dirname, exists, join

import tqdm
import urllib3
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk

NYC_RESTAURANTS = "https://data.cityofnewyork.us/api/views/43nn-pn8j/rows.csv?accessType=DOWNLOAD"
DATASET_PATH = join(dirname(abspath(__file__)), "nyc-restaurants.csv")
CHUNK_SIZE = 16384


def download_dataset():
    """Downloads the public dataset if not locally downlaoded
    and returns the number of rows are in the .csv file.
    """
    if not exists(DATASET_PATH):
        http = urllib3.PoolManager()
        resp = http.request("GET", NYC_RESTAURANTS, preload_content=False)

        if resp.status != 200:
            raise RuntimeError("Could not download dataset")

        with open(DATASET_PATH, mode="wb") as f:
            chunk = resp.read(CHUNK_SIZE)
            while chunk:
                f.write(chunk)
                chunk = resp.read(CHUNK_SIZE)

    with open(DATASET_PATH) as f:
        return sum([1 for _ in f]) - 1


def create_index(client):
    """Creates an index in Elasticsearch if one isn't already there."""
    client.indices.create(
        index="nyc-restaurants",
        body={
            "settings": {"number_of_shards": 1},
            "mappings": {
                "properties": {
                    "name": {"type": "text"},
                    "borough": {"type": "keyword"},
                    "cuisine": {"type": "keyword"},
                    "grade": {"type": "keyword"},
                    "location": {"type": "geo_point"},
                },
            },
        },
        ignore=400,
    )


def generate_actions():
    """Reads the file through csv.DictReader() and for each row
    yields a single document. This function is passed into the bulk()
    helper to create many documents in sequence.
    """
    with open(DATASET_PATH) as f:
        reader = csv.DictReader(f)

        for row in reader:
            doc = {
                "_id": row["CAMIS"],
                "name": row["DBA"],
                "borough": row["BORO"],
                "cuisine": row["CUISINE DESCRIPTION"],
                "grade": row["GRADE"] or None,
            }

            lat = row["Latitude"]
            lon = row["Longitude"]
            if lat not in ("", "0") and lon not in ("", "0"):
                doc["location"] = {"lat": float(lat), "lon": float(lon)}
            yield doc


def main():
    print("Loading dataset...")
    number_of_docs = download_dataset()

    client = Elasticsearch(
        # Add your cluster configuration here!
        # TODO
    )
    print("Creating an index...")
    create_index(client)

    print("Indexing documents...")
    progress = tqdm.tqdm(unit="docs", total=number_of_docs)
    successes = 0
    for ok, action in streaming_bulk(
        client=client,
        index="nyc-restaurants",
        actions=generate_actions(),
    ):
        progress.update(1)
        successes += ok
    print("Indexed %d/%d documents" % (successes, number_of_docs))


if __name__ == "__main__":
    main()
