#!/usr/bin/env python3
import time

from opensearchpy import OpenSearch

N_ELEMENTS = 5
EXPECTED_TEXT = "To Whom it May Concern:"

if __name__ == "__main__":
    print("Connecting to the OpenSearch cluster.")
    client = OpenSearch(
        hosts=[{"host": "localhost", "port": 9247}],
        http_auth=("admin", "admin"),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
    )
    print(client.info())

    initial_query = {"query": {"simple_query_string": {"fields": ["text"], "query": EXPECTED_TEXT}}}

    initial_embeddings = None
    timeout_s = 9
    sleep_s = 1

    start = time.time()
    found = False
    while time.time() - start < timeout_s and not found:
        results = client.search(index="ingest-test-destination", body=initial_query)
        hits = results["hits"]["hits"]
        if hits:
            print(f"found results after {time.time() - start}s")
            initial_embeddings = hits[0]["_source"]["embeddings"]
            found = True
            break
        print(f"Waiting {sleep_s}s before checking again")
        time.sleep(sleep_s)

    if not found:
        raise TimeoutError(
            f"timed out after {round(timeout_s, 3)}s trying to get results from opensearch"
        )

    query = {"size": 1, "query": {"knn": {"embeddings": {"vector": initial_embeddings, "k": 1}}}}

    vector_search = client.search(index="ingest-test-destination", body=query)

    found_text = vector_search["hits"]["hits"][0]["_source"]["text"]
    assert found_text == EXPECTED_TEXT, (
        f"OpenSearch dest check failed: Did not find "
        f"{EXPECTED_TEXT} in via vector search, instead: {found_text}."
    )
    print("OpenSearch vector search test was successful.")

    count = client.count(index="ingest-test-destination")["count"]

    assert int(count) == N_ELEMENTS, f"OpenSearch dst check fail: expect {N_ELEMENTS} got {count}"

    print(f"OpenSearch destination test was successful with {count} items being uploaded.")
