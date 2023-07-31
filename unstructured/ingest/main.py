#!/usr/bin/env python3
from unstructured.ingest.cli.cli import get_cmd

if __name__ == "__main__":
    ingest_cmd = get_cmd()
    ingest_cmd()
