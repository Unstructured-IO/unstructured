import json
import math
import time
from datetime import timedelta

import click
from couchbase import search
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions, SearchOptions
from couchbase.vector_search import VectorQuery, VectorSearch

index_name = "unstructured_test_search"


def get_client(username, password, connection_string) -> Cluster:
    auth = PasswordAuthenticator(username, password)
    options = ClusterOptions(auth)
    options.apply_profile("wan_development")
    cluster = Cluster(connection_string, options)
    cluster.wait_until_ready(timedelta(seconds=5))
    return cluster


@click.group(name="couchbase-ingest")
@click.option("--username", type=str)
@click.option("--password", type=str)
@click.option("--connection-string", type=str)
@click.option("--bucket", type=str)
@click.option("--scope", type=str)
@click.option("--collection", type=str)
@click.pass_context
def cli(
    ctx,
    username: str,
    password: str,
    connection_string: str,
    bucket: str,
    scope: str,
    collection: str,
):
    ctx.ensure_object(dict)
    ctx.obj["cluster"] = get_client(username, password, connection_string)


@cli.command()
@click.pass_context
def down(ctx):
    cluster: Cluster = ctx.obj["cluster"]
    bucket_name = ctx.parent.params["bucket"]
    scope_name = ctx.parent.params["scope"]
    collection_name = ctx.parent.params["collection"]

    print("deleting rows, query:", f"Delete from {bucket_name}.{scope_name}.{collection_name}")
    query_result = cluster.query(f"Delete from {bucket_name}.{scope_name}.{collection_name}")
    for row in query_result.rows():
        print(row)


@cli.command()
@click.option("--expected-docs", type=int, required=True)
@click.pass_context
def check(ctx, expected_docs):
    cluster: Cluster = ctx.obj["cluster"]
    bucket_name = ctx.parent.params["bucket"]
    scope_name = ctx.parent.params["scope"]
    collection_name = ctx.parent.params["collection"]

    # Tally up the embeddings
    query_result = cluster.query(f"Select * from {bucket_name}.{scope_name}.{collection_name}")
    docs = list(query_result)
    number_of_docs = len(docs)

    # Check that the assertion is true
    assert number_of_docs == expected_docs, (
        f"Number of rows in generated table ({number_of_docs})"
        f"doesn't match expected value: {expected_docs}"
    )


@cli.command()
@click.option("--output-json", type=click.File())
@click.pass_context
def check_vector(ctx, output_json):
    json_content = json.load(output_json)
    exact_embedding = json_content[0]["embeddings"]
    exact_text = json_content[0]["text"]

    print("exact embedding:", len(exact_embedding), exact_embedding)

    cluster: Cluster = ctx.obj["cluster"]
    bucket_name = ctx.parent.params["bucket"]
    scope_name = ctx.parent.params["scope"]

    search_req = search.SearchRequest.create(
        VectorSearch.from_vector_query(VectorQuery("embedding", exact_embedding, 2))
    )

    bucket = cluster.bucket(bucket_name)
    scope = bucket.scope(scope_name)

    attempts = 0
    max_attempts = 10
    rows = None
    while attempts < max_attempts:
        try:
            search_iter = scope.search(
                index_name,
                search_req,
                SearchOptions(
                    limit=2,
                    fields=["text"],
                ),
            )

            rows = list(search_iter.rows())
            if rows:
                break
        except Exception as e:
            print(f"Attempts: ({attempts}/{max_attempts}), Error while performing search:{e}")
        finally:
            attempts += 1
            time.sleep(5)

    assert 2 >= len(rows) >= 1  # only 1 or 2 length list

    assert math.isclose(rows[0].score, 1.0, abs_tol=1e-4)
    assert rows[0].fields["text"] == exact_text

    if len(rows) == 2:
        assert not math.isclose(rows[1].score, 1, abs_tol=1e-4)
        assert rows[1].fields["text"] != exact_text


if __name__ == "__main__":
    cli()
