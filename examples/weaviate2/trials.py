import os
import time
import uuid

import weaviate
from weaviate.util import get_valid_uuid

from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import DataSourceMetadata
from unstructured.partition.json import partition_json

# from weaviate.embedded import EmbeddedOptions

LOGS = []
ERROR_LOGS = []


def find_files_recursive(folder_path):
    file_list = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_list.append(file_path)

    return file_list


def get_chunks(elements):
    for element in elements:
        if not type(element.metadata.data_source) is DataSourceMetadata:
            # note: data_source attribute is assigned as a dict and this breaks chunking
            delattr(element.metadata, "data_source")

    chunks = chunk_by_title(elements)

    for i in range(len(chunks)):
        # import pdb; pdb.set_trace()
        chunks[i] = {"last_modified": chunks[i].metadata.last_modified, "text": chunks[i].text}

    return chunks


def get_weaviate():
    WEAVIATE_URL = os.environ.get("WEAVIATE_URL")
    WEAVIATE_API_KEY = os.environ.get("WEAVIATE_API_KEY")
    COHERE_KEY = os.environ.get("COHERE_API_KEY")
    OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

    auth_config = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)

    client = weaviate.Client(
        url=WEAVIATE_URL,
        auth_client_secret=auth_config,
        additional_headers={"X-Cohere-API-Key": COHERE_KEY, "X-OpenAI-API-Key": OPENAI_KEY},
    )

    return client


def get_schema():
    # vectorizer = "text2vec-huggingface"
    vectorizer = "text2vec-openai"
    # vectorizer = "none"
    schema = {
        # xml, eml, pdf, xlsx, docx
        "classes": [
            {
                "class": "myfiletype",
                "description": "a file type",
                "vectorizer": vectorizer,
                "moduleConfig": {"reranker-cohere": {"model": "rerank-multilingual-v2.0"}},
                "properties": [
                    {
                        "name": "last_modified",
                        "dataType": ["text"],
                        "description": "Last modified date for the document",
                        "moduleConfig": {
                            vectorizer: {
                                "skip": True,  # not including the this property for vectorization
                            },
                        },
                    },
                    {
                        "name": "text",
                        "dataType": ["text"],
                        "description": "Text content for the document",
                    },
                ],
            },
        ],
    }
    return schema


def upload_schema(my_schema, weaviate):
    weaviate.schema.delete_all()
    weaviate.schema.create(my_schema)


def get_file_using_query(weaviate, query_str):
    return (
        weaviate.query.get("myfiletype", ["text", "last_modified"])
        .with_hybrid(query_str, alpha=0.5)
        .with_additional(["vector"])
        .do()
    )


def get_request_object_for_ranking(query):
    return """
            {
            Get {
                Myfiletype(
                nearText: {
                    concepts: "QUERYSTR"
                }
                limit: 10
                ) {
                text
                last_modified
                _additional {
                    distance
                    rerank(
                    property: "text"
                    query: "QUERYSTR"
                    ) {
                    score
                    }
                }
                }
            }
            }
            """.replace(
        "QUERYSTR",
        query,
    )


def add_data_to_weaviate(files, weaviate):
    for filename in files:
        try:
            elements = partition_json(filename=filename)
            chunks = get_chunks(elements)
            msg = f"\n\n{str(filename)} is succesfully processed."
            LOGS.append(msg)
        except IndexError:
            error_msg = f"\n\nindex error for {filename}"
            ERROR_LOGS.append(error_msg)
            continue

        for i, chunk in enumerate(chunks):
            weaviate.batch.add_data_object(
                data_object=chunk,
                class_name="myfiletype",
                uuid=get_valid_uuid(uuid.uuid4()),
            )
            msg = f"chunk {i} is added"
            LOGS.append(msg)
            time.sleep(0.01)

    weaviate.batch.flush()
    print("\n\n-----\n\n", "Batch flushed")


def get_batch_with_cursor(client, class_name, class_properties, batch_size, cursor=None):
    query = (
        client.query.get(class_name, class_properties)
        # Optionally retrieve the vector embedding by adding `vector` to the _additional fields
        # .with_additional(["id vector"])
        .with_limit(batch_size)
    )

    if cursor is not None:
        return query.with_after(cursor).do()
    else:
        return query.do()


def delete_objects(weaviate):
    weaviate.batch.delete_objects(
        class_name="myfiletype",
        where={"path": ["text"], "operator": "Like", "valueText": "*"},
    )


def main():
    # pip install weaviate-client here
    # I've created a WCS instance: https://console.weaviate.cloud/create-cluster
    weaviate = get_weaviate()

    # # import pdb; pdb.set_trace()
    # my_schema = get_schema()

    # upload_schema(my_schema,
    #                 weaviate=weaviate)

    # files = find_files_recursive("data/results")

    # add_data_to_weaviate(files=files,
    #                      weaviate=weaviate)

    # response = get_file_using_query(weaviate=weaviate,
    #                 query_str="Ryan")

    # delete_objects(weaviate=weaviate)

    print("Sending query request")

    # response = get_batch_with_cursor(client=weaviate,
    #                       class_name="myfiletype",
    #                       class_properties=["text","last_modified"],
    #                       batch_size=2)

    # response = get_file_using_query(weaviate=weaviate,
    #                      query_str="Ryan")

    # import pdb; pdb.set_trace()

    for log in LOGS:
        print(log)
    for log in ERROR_LOGS:
        print(log)

    query = "Scientific investments in Asia"
    request_object = get_request_object_for_ranking(query)
    response = weaviate.query.raw(request_object)
    print(response)
    print(query, "\n\n\n---\n")

    query = "My email to Patricia"
    request_object = get_request_object_for_ranking(query)
    response = weaviate.query.raw(request_object)
    print(response)
    print(query, "\n\n\n---\n")

    query = "Information on the planets"
    request_object = get_request_object_for_ranking(query)
    response = weaviate.query.raw(request_object)
    print(response)
    print(query, "\n\n\n---\n")


if __name__ == "__main__":
    main()
