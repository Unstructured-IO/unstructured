from python:3.8-slim-buster

COPY unstructured unstructured
COPY README.md README.md
COPY requirements/dev.txt requirements-dev.txt

RUN apt-get update; apt-get install -y gcc 
RUN pip install -r requirements-dev.txt
