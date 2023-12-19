#!/usr/bin/env python3

import pandas as pd
from opensearchpy import OpenSearch
from opensearchpy import Document, Text, Keyword

DATA_PATH = "scripts/opensearch-test-helpers/wiki_movie_plots_small.csv"
CLUSTER_URL = "http://localhost:9200"
INDEX_NAME = "movies"


class Movie(Document):
    title = Text(fields={'raw': Keyword()})
    year = Text()
    director = Text()
    cast = Text()
    genre = Text()
    wiki_page = Text()

    class Index:
        name = "movies"

    def save(self, ** kwargs):
        return super(Movie, self).save(** kwargs)

print("Connecting to the OpenSearch cluster.")
client = OpenSearch(hosts = [{'host': "localhost", 'port': 9200}], http_auth=("admin", "admin"))
print(client.info())
df = pd.read_csv(DATA_PATH).dropna().reset_index()

try:
    response = client.indices.delete( index = 'movies')
except:
    pass

print("Creating an OpenSearch index for testing opensearch ingest.")
response = client.indices.create(index=INDEX_NAME)
if response.get("acknowledged") != True:
    raise RuntimeError("failed to create index")

for i,row in df.iterrows():
    Movie.init(using=client)
    movie = Movie(meta={'id': i}, title=row["Title"], year=row["Release Year"], director=row["Director"], cast=row["Cast"], genre=row["Genre"], wiki_page=row["Wiki Page"])
    movie.save(using=client)

client.count()

print("Successfully created and filled an OpenSearch index for testing opensearch ingest.")
