FROM quay.io/unstructured-io/base-images:wolfi-base-9b05821@sha256:7ae732aa190348e121899b9699c660bacde2d3659f854d6014044cff9d22e0ed as base

USER root

WORKDIR /app

COPY ./requirements requirements/
COPY unstructured unstructured
COPY test_unstructured test_unstructured
COPY example-docs example-docs
COPY scripts/install-paddleocr.sh install-paddleocr.sh

RUN chown -R notebook-user:notebook-user /app && \
  apk add font-ubuntu && \
  fc-cache -fv && \
  ln -s /usr/bin/python3.11 /usr/bin/python3

USER notebook-user

RUN find requirements/ -type f -name "*.txt" -exec pip3.11 install --no-cache-dir --user -r '{}' ';' && \
  ./install-paddleocr.sh && rm install-paddleocr.sh && \
  python3.11 -c "import nltk; nltk.download('punkt')" && \
  python3.11 -c "import nltk; nltk.download('averaged_perceptron_tagger')" && \
  python3.11 -c "from unstructured.partition.model_init import initialize; initialize()" && \
  python3.11 -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

ENV PATH="${PATH}:/home/notebook-user/.local/bin"
ENV TESSDATA_PREFIX=/usr/local/share/tessdata

CMD ["/bin/bash"]
