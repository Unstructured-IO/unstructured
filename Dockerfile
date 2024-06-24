FROM quay.io/unstructured-io/base-images:wolfi-base@sha256:753fa1ed5a4793eb2bb179c07a34ba9164ac46328642e2db615259274b0c9baf as base

USER root

WORKDIR /app

COPY ./requirements requirements/
COPY unstructured unstructured
COPY test_unstructured test_unstructured
COPY example-docs example-docs

RUN chown -R notebook-user:notebook-user /app && ln -s /usr/bin/python3.11 /usr/bin/python3

USER notebook-user

RUN find requirements/ -type f -name "*.txt" -exec pip3.11 install --no-cache-dir --user -r '{}' ';'
RUN pip3.11 install unstructured.paddlepaddle

RUN python3.11 -c "import nltk; nltk.download('punkt')" && \
  python3.11 -c "import nltk; nltk.download('averaged_perceptron_tagger')" && \
  python3.11 -c "from unstructured.partition.model_init import initialize; initialize()" && \
  python3.11 -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

ENV PATH="${PATH}:/home/notebook-user/.local/bin"
ENV TESSDATA_PREFIX=/usr/local/share/tessdata

CMD ["/bin/bash"]
