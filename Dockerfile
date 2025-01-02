FROM quay.io/unstructured-io/base-images:wolfi-base-latest as base

USER root

WORKDIR /app

COPY ./requirements requirements/
COPY unstructured unstructured
COPY test_unstructured test_unstructured
COPY example-docs example-docs

# Copy the downloaded NLTK data folder to your local environment.s
COPY ./nltk_data /home/notebook-user/nltk_data

RUN chown -R notebook-user:notebook-user /app && \
    apk add font-ubuntu git && \
    fc-cache -fv && \
    [ -e /usr/bin/python3 ] || ln -s /usr/bin/python3.11 /usr/bin/python3

USER notebook-user

RUN find requirements/ -type f -name "*.txt" -exec pip3.11 install --no-cache-dir --user -r '{}' ';'

# Command to check if NLTK data has been copied correctly
RUN python3.11 -c "import nltk; print(nltk.data.find('tokenizers/punkt_tab'))" 

RUN python3.11 -c "from unstructured.partition.model_init import initialize; initialize()" && \
    python3.11 -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

ENV PATH="${PATH}:/home/notebook-user/.local/bin"
ENV TESSDATA_PREFIX=/usr/local/share/tessdata
ENV NLTK_DATA=/home/notebook-user/nltk_data

CMD ["/bin/bash"]
