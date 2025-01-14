FROM quay.io/unstructured-io/base-images:wolfi-base-latest AS base

ARG PYTHON=python3.11
ARG PIP=pip3.11

USER root

WORKDIR /app

COPY ./requirements requirements/
COPY unstructured unstructured
COPY test_unstructured test_unstructured
COPY example-docs example-docs

RUN chown -R notebook-user:notebook-user /app && \
    apk add font-ubuntu git && \
    fc-cache -fv && \
    [ -e /usr/bin/python3 ] || ln -s /usr/bin/$PYTHON /usr/bin/python3

USER notebook-user

ENV NLTK_DATA=/home/notebook-user/nltk_data

# Install Python dependencies and download required NLTK packages
RUN find requirements/ -type f -name "*.txt" -exec $PIP install --no-cache-dir --user -r '{}' ';' && \
    mkdir -p ${NLTK_DATA} && \
    $PYTHON -m nltk.downloader -d ${NLTK_DATA} punkt_tab averaged_perceptron_tagger_eng && \
    $PYTHON -c "from unstructured.partition.model_init import initialize; initialize()" && \
    $PYTHON -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

ENV PATH="${PATH}:/home/notebook-user/.local/bin"
ENV TESSDATA_PREFIX=/usr/local/share/tessdata

CMD ["/bin/bash"]
