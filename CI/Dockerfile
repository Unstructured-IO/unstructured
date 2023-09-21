FROM ubuntu:22.04 as base
RUN apt-get update && apt-get upgrade -y && apt-get install -y software-properties-common


FROM base as python-install
RUN apt-get install -y python3 python3-pip python3.10-venv
RUN ln -s /usr/bin/python3 /usr/bin/python

FROM python-install as python-deps
RUN apt-get install make
WORKDIR /unstructured
COPY Makefile .
COPY requirements requirements
COPY scripts scripts
RUN python -m venv .venv && \
    . .venv/bin/activate && \
    make install-ci

FROM python-deps as run-deps
RUN apt-get install -y libmagic-dev poppler-utils libreoffice pandoc && \
    add-apt-repository -y ppa:alex-p/tesseract-ocr5 && apt-get update && \
    apt-get install -y tesseract-ocr tesseract-ocr-kor diffstat
RUN . .venv/bin/activate && \
    make install-ingest-s3 && \
    make install-ingest-airtable && \
    make install-ingest-azure && \
    make install-ingest-box && \
    make install-ingest-confluence && \
    make install-ingest-discord && \
    make install-ingest-elasticsearch && \
    make install-ingest-dropbox && \
    make install-ingest-gcs && \
    make install-ingest-google-drive && \
    make install-ingest-github && \
    make install-ingest-gitlab && \
    make install-ingest-jira && \
    make install-ingest-onedrive && \
    make install-ingest-outlook && \
    make install-ingest-salesforce && \
    make install-ingest-slack && \
    make install-ingest-wikipedia && \
    make install-ingest-notion && \
    make install-ingest-delta-table

FROM run-deps as run
COPY unstructured unstructured
COPY test_unstructured_ingest test_unstructured_ingest

ENTRYPOINT ["./test_unstructured_ingest/test-ingest.sh"]
