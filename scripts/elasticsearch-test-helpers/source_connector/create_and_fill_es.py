#!/usr/bin/env python3

import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from es_cluster_config import (
    CLUSTER_URL,
    DATA_PATH,
    INDEX_NAME,
    MAPPINGS,
    form_elasticsearch_doc_dict,
)

from unstructured.ingest.logger import logger

logger.info("Connecting to the Elasticsearch cluster.")
es = Elasticsearch(CLUSTER_URL, basic_auth=("elastic", "DkIedPPSCb"), request_timeout=30)
logger.info(f"{es.info()}")
df = pd.read_csv(DATA_PATH).dropna().reset_index()

logger.info("Creating an Elasticsearch index for testing elasticsearch ingest.")
response = es.options(max_retries=5).indices.create(index=INDEX_NAME, mappings=MAPPINGS)
if response.meta.status != 200:
    raise RuntimeError("failed to create index")

logger.info("Loading data into the index.")
bulk_data = []
for i, row in df.iterrows():
    bulk_data.append(form_elasticsearch_doc_dict(i, row))
bulk(es, bulk_data)

es.indices.refresh(index=INDEX_NAME)
response = es.cat.count(index=INDEX_NAME, format="json")

logger.info(
    "Successfully created and filled an Elasticsearch index for testing elasticsearch ingest."
)
