import os

DATA_PATH = "scripts/elasticsearch-test-helpers/source_connector/wiki_movie_plots_small.csv"
CLUSTER_URL = "http://localhost:9200"
INDEX_NAME = "movies"
USER = os.environ["ELASTIC_USER"]
PASSWORD = os.environ["ELASTIC_PASSWORD"]

MAPPINGS = {
    "properties": {
        "title": {"type": "text", "analyzer": "english"},
        "ethnicity": {"type": "text", "analyzer": "standard"},
        "director": {"type": "text", "analyzer": "standard"},
        "cast": {"type": "text", "analyzer": "standard"},
        "genre": {"type": "text", "analyzer": "standard"},
        "plot": {"type": "text", "analyzer": "english"},
        "year": {"type": "integer"},
        "wiki_page": {"type": "keyword"},
    },
}


def form_elasticsearch_doc_dict(i, csv_row):
    return {
        "_index": INDEX_NAME,
        "_id": i,
        "_source": {
            "title": csv_row["Title"],
            "ethnicity": csv_row["Origin/Ethnicity"],
            "director": csv_row["Director"],
            "cast": csv_row["Cast"],
            "genre": csv_row["Genre"],
            "plot": csv_row["Plot"],
            "year": csv_row["Release Year"],
            "wiki_page": csv_row["Wiki Page"],
        },
    }
