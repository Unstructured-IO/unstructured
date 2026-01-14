FROM cgr.dev/chainguard/wolfi-base:latest AS base

ARG PYTHON=python3.12
ARG PIP="${PYTHON} -m pip"

USER root

WORKDIR /app

COPY ./requirements requirements/
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
    apk cache clean && \
    ln -s /usr/lib/libreoffice/program/soffice.bin /usr/bin/libreoffice && \
    ln -s /usr/lib/libreoffice/program/soffice.bin /usr/bin/soffice && \
    chmod +x /usr/lib/libreoffice/program/soffice.bin && \
    chown -R notebook-user:notebook-user /app && \
    apk add --no-cache font-ubuntu fontconfig git && \
    apk upgrade --no-cache py3.12-pip && \
    fc-cache -fv && \
    [ -e /usr/bin/python3 ] || ln -s /usr/bin/$PYTHON /usr/bin/python3

ARG NB_UID=1000
ARG NB_USER=notebook-user
RUN addgroup --gid ${NB_UID} ${NB_USER} && \
    adduser --disabled-password --gecos "" --uid ${NB_UID} -G ${NB_USER} ${NB_USER}

ENV USER=${NB_USER}
ENV HOME=/home/${NB_USER}
COPY --chown=${NB_USER} scripts/initialize-libreoffice.sh ${HOME}/initialize-libreoffice.sh
RUN ${HOME}/initialize-libreoffice.sh && rm ${HOME}/initialize-libreoffice.sh

USER notebook-user

# append PATH before pip install to avoid warning logs; it also avoids issues with packages that needs compilation during installation
ENV PATH="${PATH}:/home/notebook-user/.local/bin"
ENV TESSDATA_PREFIX=/usr/local/share/tessdata
ENV NLTK_DATA=/home/notebook-user/nltk_data

# Upgrade pip to fix CVE-2025-8869
RUN $PIP install --no-cache-dir --user --upgrade "pip>=25.3"

# Install Python dependencies and download required NLTK packages
RUN find requirements/ -type f -name "*.txt" ! -name "test.txt" ! -name "dev.txt" ! -name "constraints.txt" -exec $PIP install --no-cache-dir --user -r '{}' ';' && \
    mkdir -p ${NLTK_DATA} && \
    $PYTHON -m nltk.downloader -d ${NLTK_DATA} punkt_tab averaged_perceptron_tagger_eng && \
    $PYTHON -c "from unstructured.partition.model_init import initialize; initialize()" && \
    $PYTHON -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

ENV HF_HUB_OFFLINE=1

CMD ["/bin/bash"]
