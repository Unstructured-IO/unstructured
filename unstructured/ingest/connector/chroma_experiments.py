import json

import chromadb
from unstructured.staging.base import flatten_dict


#todo: in ingest/cli/interfaces.py add help for chunking

e="/Users/davidpotter/Documents/Unstructured/sessions/unstructured/test_unstructured_ingest/workdir/s3-pinecone-dest/embedded/42d06000044204b602333f8d3a0f592d.json"
with open(e) as read_content: 
    ed=(json.load(read_content))


chroma_client = chromadb.PersistentClient(path="/Users/davidpotter/Documents/Unstructured/sessions/unstructured/test_unstructured_ingest/chromadb/")

collection = chroma_client.get_or_create_collection(name="my_collection")

# collection.add(
#     documents=["This is a document", "This is another document"],
#     metadatas=[{"source": "my_source"}, {"source": "my_source"}],
#     ids=["id1", "id2"]
# )
# print([x.get("embeddings") for x in ed])
# This worked??
lll=ed[0]["metadata"]
print(lll)
breakpoint()

print([flatten_dict(x.get("metadata"),separator=".",flatten_lists=True) for x in ed])
breakpoint()

collection.add(
    documents=[x.get("text") for x in ed],
    embeddings=[x.get("embeddings") for x in ed],
    # metadatas=[x.get("metadata") for x in ed],
    metadatas=[flatten_dict(x.get("metadata"),separator=".",flatten_lists=True) for x in ed],
    ids=[x.get("element_id") for x in ed]
)
# breakpoint()

# print(collection.get(include=["embeddings", "documents", "metadatas"]))

# results = collection.query(
#     query_texts=["who knows everything?"],
#     n_results=1
# )

# print(results)
print(collection.peek())
print(collection.count())

chroma_client.delete_collection(name="my_collection")