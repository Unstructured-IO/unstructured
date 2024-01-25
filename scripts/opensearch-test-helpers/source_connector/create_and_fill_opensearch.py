#!/usr/bin/env python3
from contextlib import suppress

import pandas as pd
from opensearchpy import Document, Keyword, OpenSearch, Text
from opensearchpy.exceptions import NotFoundError

DATA_PATH = "scripts/opensearch-test-helpers/wiki_movie_plots_small.csv"
CLUSTER_URL = "http://localhost:9200"
INDEX_NAME = "movies"


class Movie(Document):
    title = Text(fields={"raw": Keyword()})
    year = Text()
    director = Text()
    cast = Text()
    genre = Text()
    wiki_page = Text()
    ethnicity = Text()
    plot = Text()

    class Index:
        name = "movies"

    def save(self, **kwargs):
        return super(Movie, self).save(**kwargs)


print("Connecting to the OpenSearch cluster.")
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", "admin"),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False,
)
print(client.info())
df = pd.read_csv(DATA_PATH).dropna().reset_index()

with suppress(NotFoundError):
    client.indices.delete(index="movies")

print("Creating an OpenSearch index for testing opensearch ingest.")
response = client.indices.create(index=INDEX_NAME)
if not response.get("acknowledged"):
    raise RuntimeError("failed to create index")

for i, row in df.iterrows():
    Movie.init(using=client)
    movie = Movie(
        meta={"id": i},
        title=row["Title"],
        year=row["Release Year"],
        director=row["Director"],
        cast=row["Cast"],
        genre=row["Genre"],
        wiki_page=row["Wiki Page"],
        ethnicity=row["Origin/Ethnicity"],
        plot=row["Plot"],
    )
    movie.save(using=client)

client.count()

print("Successfully created and filled an OpenSearch index for testing opensearch ingest.")
