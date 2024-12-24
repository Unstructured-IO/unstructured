FROM quay.io/unstructured-io/base-images:wolfi-base-latest as base

USER root

WORKDIR /app

COPY ./requirements requirements/
COPY unstructured unstructured
COPY test_unstructured test_unstructured
COPY example-docs example-docs

RUN chown -R notebook-user:notebook-user /app && \
    apk add --no-cache font-ubuntu git && \
    fc-cache -fv && \
    if [ "$(readlink -f /usr/bin/python3)" != "/usr/bin/python3.11" ]; then \
        ln -sf /usr/bin/python3.11 /usr/bin/python3; \
    fi

USER notebook-user

RUN find requirements/ -type f -name "*.txt" -exec pip3.11 install --no-cache-dir --user -r '{}' \;

RUN python3.11 -c "import os; os.makedirs('/home/notebook-user/nltk_data', exist_ok=True)" && \
    python3.11 -c "from nltk.downloader import download; download('punkt_tab'); download('averaged_perceptron_tagger_eng')"

RUN python3.11 -c "from unstructured.nlp.tokenize import download_nltk_packages; download_nltk_packages()"

RUN python3.11 -c "from unstructured.partition.model_init import initialize; initialize()"

RUN python3.11 -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; \
    model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

ENV PATH="${PATH}:/home/notebook-user/.local/bin"
ENV TESSDATA_PREFIX=/usr/local/share/tessdata

CMD ["/bin/bash"]
