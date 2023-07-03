import os
import sys
import time

from unstructured.partition.auto import partition


def warm_up_process(filename):
    warmup_dir = os.path.join(os.path.dirname(__file__), "warmup-docs")
    warmup_file = os.path.join(warmup_dir, f"warmup{os.path.splitext(filename)[1]}")

    if os.path.exists(warmup_file):
        partition(warmup_file, strategy="fast")
    else:
        partition(filename, strategy="fast")


def measure_execution_time(filename, iterations, strategy):
    total_time = 0.0

    for _ in range(iterations):
        start_time = time.time()
        partition(filename, strategy=strategy)
        end_time = time.time()
        execution_time = end_time - start_time
        total_time += execution_time

    average_time = total_time / iterations
    print("Average time:", average_time)


if __name__ == "__main__":
    filename = sys.argv[1]
    iterations = int(sys.argv[2])
    strategy = sys.argv[3]

    warm_up_process(filename)
    measure_execution_time(filename, iterations, strategy)
