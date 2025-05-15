FROM quay.io/unstructured-io/base-images:wolfi-py3.12-slim-82e1186

ARG PYTHON=python3.12

USER root
WORKDIR /app

RUN addgroup -S notebook-user && adduser -S notebook-user -G notebook-user

RUN apk add --no-cache mesa-gl glib

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
COPY unstructured unstructured
COPY test_unstructured test_unstructured
COPY example-docs example-docs

RUN chown -R notebook-user:notebook-user /app

USER notebook-user

ENV PATH="/home/notebook-user/.local/bin:$PATH"
ENV TESSDATA_PREFIX=/usr/local/share/tessdata
ENV NLTK_DATA=/home/notebook-user/nltk_data

RUN uv sync && \
    mkdir -p ${NLTK_DATA} && \
    .venv/bin/python -m nltk.downloader -d ${NLTK_DATA} punkt_tab averaged_perceptron_tagger_eng && \
    .venv/bin/python -c "from unstructured.partition.model_init import initialize; initialize()" && \
    .venv/bin/python -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

CMD ["/bin/bash"]
