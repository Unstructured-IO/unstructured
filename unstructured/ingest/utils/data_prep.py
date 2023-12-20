import itertools
import json


def chunk_generator(iterable, batch_size=100):
    """A helper function to break an iterable into chunks of size batch_size."""
    it = iter(iterable)
    chunk = tuple(itertools.islice(it, batch_size))
    while chunk:
        yield chunk
        chunk = tuple(itertools.islice(it, batch_size))


def generator_batching_wbytes(iterable, batch_size_limit_bytes=15_000_000):
    """A helper function to break an iterable into chunks of specified bytes."""
    current_batch, current_batch_size = [], 0

    for item in iterable:
        item_size_bytes = len(json.dumps(item).encode("utf-8"))

        if current_batch_size + item_size_bytes <= batch_size_limit_bytes:
            current_batch.append(item)
            current_batch_size += item_size_bytes
        else:
            yield current_batch
            current_batch, current_batch_size = [item], item_size_bytes

    if current_batch:
        yield current_batch
