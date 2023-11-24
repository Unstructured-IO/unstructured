DATA_PATH = "scripts/elasticsearch-test-helpers/wiki_movie_plots_small.csv"
CLUSTER_URL = "http://localhost:9200"
INDEX_NAME = "ingest-test-destination"

# TODO-dest make this a json and load via there
MAPPINGS = {
    "properties": {
        "a": {"type": "text", "analyzer": "english"},
        "b": {"type": "text", "analyzer": "standard"},
        "c": {"type": "integer"},
        "d": {"type": "keyword"},
    },
}
