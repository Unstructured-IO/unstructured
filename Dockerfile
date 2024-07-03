FROM quay.io/unstructured-io/base-images:wolfi-base-d46498e@sha256:3db0544df1d8d9989cd3c3b28670d8b81351dfdc1d9129004c71ff05996fd51e as base

USER root

WORKDIR /app

COPY ./requirements requirements/
COPY unstructured unstructured
COPY test_unstructured test_unstructured
COPY example-docs example-docs

RUN chown -R notebook-user:notebook-user /app && \
  apk add font-ubuntu && \
  fc-cache -fv && \
  ln -s /usr/bin/python3.11 /usr/bin/python3

USER notebook-user

RUN find requirements/ -type f -name "*.txt" -exec pip3.11 install --no-cache-dir --user -r '{}' ';' && \
  pip3.11 install unstructured.paddlepaddle && \
  python3.11 -c "import nltk; nltk.download('punkt')" && \
  python3.11 -c "import nltk; nltk.download('averaged_perceptron_tagger')" && \
  python3.11 -c "from unstructured.partition.model_init import initialize; initialize()" && \
  python3.11 -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

ENV PATH="${PATH}:/home/notebook-user/.local/bin"
ENV TESSDATA_PREFIX=/usr/local/share/tessdata

CMD ["/bin/bash"]
