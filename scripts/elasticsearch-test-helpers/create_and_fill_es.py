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

print("Connecting to the Elasticsearch cluster.")
es = Elasticsearch(CLUSTER_URL)
print(es.info())
df = pd.read_csv(DATA_PATH).dropna().reset_index()

print("Creating an Elasticsearch index for testing elasticsearch ingest.")
es.indices.create(index=INDEX_NAME, mappings=MAPPINGS)

print("Loading data into the index.")
bulk_data = []
for i, row in df.iterrows():
    bulk_data.append(form_elasticsearch_doc_dict(i, row))
bulk(es, bulk_data)

es.indices.refresh(index=INDEX_NAME)
response = es.cat.count(index=INDEX_NAME, format="json")

print("Succesfully created and filled an Elasticsearch index for testing elasticsearch ingest.")
