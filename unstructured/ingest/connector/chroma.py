import json

import chromadb

# try:
#     docsearch = chromadb.from_documents(documents=..., embedding=...)
# except InvalidDimensionException:
#     chromadb().delete_collection()
#     docsearch = chromadb.from_documents(documents=..., embedding=...)

def flatten_values(value, seperator="\n", no_value_str=""):
    """Flattens list or dict objects. Joins each value or item with
    the seperator character. Keys are not included in the joined string.
    When a dict value or a list item is None, no_value_str is used to
    represent that value / item."""
    if value is None:
        return no_value_str

    if isinstance(value, list):
        flattened_values = [flatten_values(item, seperator) for item in value]
        return seperator.join(flattened_values)

    elif isinstance(value, dict):
        flattened_values = [flatten_values(item, seperator) for item in value.values()]
        return seperator.join(flattened_values)

    else:
        return str(value)


e="/Users/davidpotter/Documents/Unstructured/sessions/unstructured/test_unstructured_ingest/workdir/s3-pinecone-dest/embedded/42d06000044204b602333f8d3a0f592d.json"
with open(e) as read_content: 
    ed=(json.load(read_content))


breakpoint()
chroma_client = chromadb.PersistentClient(path="/Users/davidpotter/Documents/Unstructured/sessions/unstructured/test_unstructured_ingest/chromadb/")

collection = chroma_client.get_or_create_collection(name="my_collection")

# collection.add(
#     documents=["This is a document", "This is another document"],
#     metadatas=[{"source": "my_source"}, {"source": "my_source"}],
#     ids=["id1", "id2"]
# )
# print([x.get("embeddings") for x in ed])
# This worked??
md={"data_source":{"url":"example-docs/book-war-and-peace-1p.txt","date_created":"2023-10-2510:05:44.916316","date_modified":"2023-10-2510:05:44.916316"}}
print(flatdict.FlatterDict(md,delimiter="."))
breakpoint()
metadatas=[md for x in ed],
print(metadatas)
collection.add(
    documents=[x.get("text") for x in ed],
    embeddings=[x.get("embeddings") for x in ed],
    # metadatas=[x.get("metadata") for x in ed],
    metadatas=[dict(flatdict.FlatterDict(x.get("metadata"),delimiter=".")) for x in ed],
    ids=[x.get("element_id") for x in ed]
)
# breakpoint()

# print(collection.get(include=["embeddings", "documents", "metadatas"]))

# results = collection.query(
#     query_texts=["who knows everything?"],
#     n_results=1
# )

# print(results)
print(collection.count())

chroma_client.delete_collection(name="my_collection")