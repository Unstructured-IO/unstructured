FROM cgr.dev/chainguard/wolfi-base:latest AS base

ARG PYTHON=python3.12

USER root

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY unstructured unstructured
COPY test_unstructured test_unstructured
COPY example-docs example-docs
COPY ./docker/packages/*.apk /tmp/packages/

RUN apk update && \
    apk add libxml2 python-3.12 python-3.12-base py3.12-pip glib \
      mesa-gl mesa-libgallium cmake bash libmagic wget git openjpeg \
      poppler poppler-utils poppler-glib libreoffice tesseract && \
    apk add --allow-untrusted /tmp/packages/pandoc-3.1.8-r0.apk && \
    rm -rf /tmp/packages && \
    git clone --depth 1 https://github.com/tesseract-ocr/tessdata.git /tmp/tessdata && \
    mkdir -p /usr/local/share/tessdata && \
    cp /tmp/tessdata/*.traineddata /usr/local/share/tessdata && \
    rm -rf /tmp/tessdata && \
    git clone --depth 1 https://github.com/tesseract-ocr/tessconfigs /tmp/tessconfigs && \
    cp -r /tmp/tessconfigs/configs /usr/local/share/tessdata && \
    cp -r /tmp/tessconfigs/tessconfigs /usr/local/share/tessdata && \
    rm -rf /tmp/tessconfigs && \
    apk cache clean && \
    ln -s /usr/lib/libreoffice/program/soffice.bin /usr/bin/libreoffice && \
    ln -s /usr/lib/libreoffice/program/soffice.bin /usr/bin/soffice && \
    chmod +x /usr/lib/libreoffice/program/soffice.bin && \
    apk add --no-cache font-ubuntu fontconfig && \
    apk upgrade --no-cache py3.12-pip && \
    fc-cache -fv && \
    ln -sf /usr/bin/$PYTHON /usr/bin/python3

ARG NB_UID=1000
ARG NB_USER=notebook-user
RUN addgroup --gid ${NB_UID} ${NB_USER} && \
    adduser --disabled-password --gecos "" --uid ${NB_UID} -G ${NB_USER} ${NB_USER}

ENV USER=${NB_USER}
ENV HOME=/home/${NB_USER}
COPY --chown=${NB_USER} scripts/initialize-libreoffice.sh ${HOME}/initialize-libreoffice.sh

# Remove unused Python versions
RUN rm -rf /usr/lib/python3.10 && \
    rm -rf /usr/lib/python3.11 && \
    rm -rf /usr/lib/python3.13 && \
    rm /usr/bin/python3.13

# Install uv (as root, into a system-wide location)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Hand /app to notebook-user before switching to that user.
# This must happen before uv sync so it can create .venv inside /app.
RUN chown -R ${NB_USER}:${NB_USER} /app

USER notebook-user
WORKDIR ${HOME}

# Initialize libreoffice config as non-root user (required for soffice to work properly)
# See: https://github.com/Unstructured-IO/unstructured/issues/3105
RUN ./initialize-libreoffice.sh && rm initialize-libreoffice.sh

WORKDIR /app

ENV TESSDATA_PREFIX=/usr/local/share/tessdata
ENV NLTK_DATA=/home/notebook-user/nltk_data
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_DOWNLOADS=never

# Install Python dependencies via uv and download required NLTK packages
RUN uv sync --frozen --all-extras --no-group dev --no-group lint --no-group test && \
    mkdir -p ${NLTK_DATA} && \
    uv run $PYTHON -m nltk.downloader -d ${NLTK_DATA} punkt_tab averaged_perceptron_tagger_eng && \
    uv run $PYTHON -c "from unstructured.partition.model_init import initialize; initialize()" && \
    uv run $PYTHON -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

ENV PATH="/app/.venv/bin:${PATH}"
ENV HF_HUB_OFFLINE=1

CMD ["/bin/bash"]
