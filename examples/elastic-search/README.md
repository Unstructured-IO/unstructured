# Loading `Unstructured` elements into `Elasticsearch`

The following example shows how to load `Unstructured` output `Element` objects into an `Elasticsearch`
index with sentiment analyis scores provided by the `TextBlob` library. 

Elasticsearch stores data as JSON documents in an index, which is a collection of documents that are related to each other. 


## Running the example

1. Run `pip install -r requirements.txt` to install the Python dependencies.
1. Modify `es-credentials.ini` with your information: `cloud_id`, `user` and `password`.
1. Run the `load-into-es.ipynb` notebook.