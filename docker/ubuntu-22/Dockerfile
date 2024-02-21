# Dockerfile that approximates the CI image
#
# Mainly useful for updating test-ingest fixtures

FROM ubuntu:22.04

COPY scripts/setup_ubuntu.sh scripts/setup_ubuntu.sh

RUN bash scripts/setup_ubuntu.sh root

COPY requirements/ requirements/
COPY Makefile Makefile

SHELL ["/bin/bash", "-c"]

RUN source ~/.bashrc && pyenv virtualenv 3.10 unstructured && \
    source ~/.pyenv/versions/unstructured/bin/activate && \
    make install-ci && \
    make install-ingest-s3 && \
    make install-ingest-azure && \
    make install-ingest-github && \
    make install-ingest-gitlab && \
    make install-ingest-wikipedia && \
    make install-ingest-discord && \
    make install install-ingest-slack && \
    make install-ingest-confluence
