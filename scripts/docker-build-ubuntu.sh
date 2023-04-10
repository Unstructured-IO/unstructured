# Mainly useful for building an image from which to update test-ingest fixtures

#!/usr/bin/env bash

docker build -t unstructured-ubuntu:latest -f docker/ubuntu-22/Dockerfile .


