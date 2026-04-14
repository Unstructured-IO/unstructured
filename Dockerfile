FROM cgr.dev/chainguard/wolfi-base:latest AS base

ARG PYTHON=python3.12

USER root

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY unstructured unstructured
COPY test_unstructured test_unstructured
COPY example-docs example-docs

RUN apk_ok=false; \
    for attempt in 1 2 3; do \
      apk update && \
      apk add libxml2 python-3.12 python-3.12-base glib \
        mesa-gl mesa-libgallium cmake bash libmagic wget git openjpeg \
        poppler poppler-utils poppler-glib libreoffice tesseract && \
      apk_ok=true && break; \
      echo "apk install failed (attempt $attempt/3), retrying in 5s..."; sleep 5; \
    done; $apk_ok && \
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
    rm -f /usr/bin/python3.13

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
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_DOWNLOADS=never

# Install Python dependencies via uv, then trigger spaCy model self-install while network is available
RUN uv sync --locked --all-extras --no-group dev --no-group lint --no-group test --no-group release && \
    uv run --no-sync $PYTHON -c "from unstructured.nlp.tokenize import _get_nlp; print('spaCy model loaded:', _get_nlp().meta['name'])" && \
    uv run --no-sync $PYTHON -c "from unstructured.partition.model_init import initialize; initialize()" && \
    uv run --no-sync $PYTHON -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

# Replace PyPI opencv wheels (which bundle vulnerable ffmpeg 5.1.x with 14 CVEs)
# with a source-built opencv-contrib-python-headless wheel compiled with
# WITH_FFMPEG=OFF + ENABLE_CONTRIB=1 + ENABLE_HEADLESS=1.
#
# The contrib-headless variant is a strict superset of the cv2 API exposed by
# opencv-python, opencv-python-headless, and opencv-contrib-python (all of
# which are pulled in transitively by unstructured-paddleocr / unstructured-
# inference). One wheel can therefore replace all three. Because the wheel's
# metadata name only matches opencv-contrib-python-headless, we have to
# uninstall the other variants first - `uv pip install --reinstall-package`
# would silently no-op for the non-matching names.
#
# See: https://github.com/opencv/opencv-python/issues/1212
ARG OPENCV_WHEEL_TAG=opencv-4.12.0.88
ARG OPENCV_WHEEL_VERSION=4.12.0.88
RUN ARCH=$(uname -m) && \
    wget -q -O /tmp/opencv.whl \
      "https://github.com/Unstructured-IO/unstructured/releases/download/${OPENCV_WHEEL_TAG}/opencv_contrib_python_headless-${OPENCV_WHEEL_VERSION}-cp312-cp312-linux_${ARCH}.whl" && \
    uv pip uninstall \
      opencv-python opencv-python-headless \
      opencv-contrib-python opencv-contrib-python-headless && \
    uv pip install --no-deps /tmp/opencv.whl && \
    rm /tmp/opencv.whl

ENV PATH="/app/.venv/bin:${PATH}"
ENV HF_HUB_OFFLINE=1

CMD ["/bin/bash"]
