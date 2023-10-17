import argparse
import os

import pinecone


def main():
    pinecone_api_key = os.environ["PINECONE_API_KEY"]

    parser = argparse.ArgumentParser(description="This script creates a Pinecone index")
    parser.add_argument(
        "--index_name",
        type=str,
        default="ingest-test",
        help="Name of the index (default: ingest-test)",
    )
    parser.add_argument(
        "--environment",
        type=str,
        default="gcp-starter",
        help="Pinecone environment (default: gcp-starter)",
    )
    parser.add_argument(
        "--dimension",
        type=int,
        default=1536,
        help="Dimension of the index (default: 1536)",
    )
    parser.add_argument(
        "--metric",
        type=str,
        default="euclidean",
        help="Metric used for the index (default: euclidean)",
    )

    args = parser.parse_args()

    pinecone.init(api_key=pinecone_api_key, environment=args.environment)

    if pinecone.list_indexes():
        print("Current indexes:", pinecone.list_indexes())
        print("No index creation due to an index existing")
    else:
        create_index(args.index_name, args.dimension, args.metric)

    print(f"Info on index named {args.index_name}:\n", pinecone.describe_index(args.index_name))


def create_index(index_name, dimension, metric):
    pinecone.create_index(index_name, dimension=dimension, metric=metric)
    print(f"Index named {index_name} created.")
    pinecone.describe_index(index_name)
    print("All indexes:")
    print(pinecone.list_indexes())


if __name__ == "__main__":
    main()
