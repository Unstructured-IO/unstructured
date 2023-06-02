import sys

from unstructured.partition.auto import partition

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Please provide the path to the file as the first argument and the strategy as the "
            "second argument.",
        )
        sys.exit(1)

    file_path = sys.argv[1]
    strategy = sys.argv[2]
    result = partition(file_path, strategy=strategy)
    # access element in the return value to make sure we got something back, otherwise error
    result[1]
