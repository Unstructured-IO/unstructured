# Performance
This is a collection of tools helpful for inspecting and tracking performance of the Unstructured library.

The benchmarking script allows a user to track performance time to partitioning results against a fixed set of test documents and store those results with indication of architecture, instance type, and git hash, in S3.

The profiling script allows a user to inspect how time time and memory are spent across called functions when performing partitioning on a given document.

## Install
Benchmarking requires no additional dependencies and should work without any initial setup.
Profiling has a few dependencies which can be installed with:

```bash
pip install -r scripts/performance/requirements.txt
npm install -g speedscope
```

The second dependency `speedscope` provides a tool to view profiling results from `py-spy` locally. Alternatively you can also drop the profile result `*.speedscope` into https://www.speedscope.app/ to view the results online.

## Run
### Benchmark
Export / assign desired environment variable settings:
- DOCKER_TEST: Set to true to run benchmark inside a Docker container (default: false)
- NUM_ITERATIONS: Number of iterations for benchmark (e.g., 100) (default: 3)
- INSTANCE_TYPE: Type of benchmark instance (e.g., "c5.xlarge") (default: unspecified)
- PUBLISH_RESULTS: Set to true to publish results to S3 bucket (default: false)
-
Usage: `./scripts/performance/benchmark.sh`

For text-classification and tokenization changes, use the representative text-path benchmark. It
warms the spaCy model, clears per-text NLP result caches between iterations, and fingerprints
element types and text so candidate results can be checked for exact output parity:

```bash
# First run on upstream/main, then switch to the candidate branch for the second command.
uv run --no-sync python scripts/performance/benchmark_text_partition.py /tmp/main.json
uv run --no-sync python scripts/performance/benchmark_text_partition.py \
  /tmp/candidate.json --compare /tmp/main.json
```

The default matrix covers large TXT, HTML, DOCX, and PPTX documents. Set `NUM_ITERATIONS` or pass
`--iterations` to change the default of three measured runs. Repeat `--input PATH` to benchmark a
custom document set instead.

### Profile

Export / assign desired environment variable settings:
- DOCKER_TEST: Set to true to run profiling inside a Docker container (default: false)

Usage:

**on Linux**: `./scripts/performance/profile.sh`

**on macOS**: `sudo -E ./scripts/performance/profile.sh`; `py-spy` requires su to run on macOS

- Run the script and choose the profiling mode: 'run' or 'view'.
- In the 'run' mode, you can profile custom files or select existing test files.
- In the 'view' mode, you can view previously generated profiling results.
- The script supports time profiling with cProfile and memory profiling with memray.
- Users can choose different visualization options such as flamegraphs, tables, trees, summaries, and statistics.
- Test documents are synced from an S3 bucket to a local directory before running the profiles
