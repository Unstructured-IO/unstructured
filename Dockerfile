FROM quay.io/unstructured-io/base-images:wolfi-base-latest as base

USER root

WORKDIR /app

COPY ./requirements requirements/
COPY unstructured unstructured
COPY test_unstructured test_unstructured
COPY example-docs example-docs

RUN chown -R notebook-user:notebook-user /app && \
  apk add font-ubuntu git && \
  fc-cache -fv && \
  ln -s /usr/bin/python3.11 /usr/bin/python3

USER notebook-user

RUN find requirements/ -type f -name "*.txt" -exec pip3.11 install --no-cache-dir --user -r '{}' ';' && \
  python3.11 -c "from unstructured.nlp.tokenize import download_nltk_packages; download_nltk_packages()" && \
  python3.11 -c "from unstructured.partition.model_init import initialize; initialize()" && \
  python3.11 -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

ENV PATH="${PATH}:/home/notebook-user/.local/bin"
ENV TESSDATA_PREFIX=/usr/local/share/tessdata

CMD ["/bin/bash"]
