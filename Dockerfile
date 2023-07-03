# syntax=docker/dockerfile:experimental
FROM quay.io/unstructured-io/base-images:rocky8.7-3 as base

ARG PIP_VERSION

# Set up environment
ENV HOME /home/
WORKDIR ${HOME}
RUN mkdir ${HOME}/.ssh && chmod go-rwx ${HOME}/.ssh \
  &&  ssh-keyscan -t rsa github.com >> /home/.ssh/known_hosts
ENV PYTHONPATH="${PYTHONPATH}:${HOME}"
ENV PATH="/home/usr/.local/bin:${PATH}"

FROM base as deps
# Copy and install Unstructured
COPY requirements requirements

RUN python3.8 -m pip install pip==${PIP_VERSION} && \
  dnf -y groupinstall "Development Tools" && \
  pip install --no-cache -r requirements/base.txt && \
  pip install --no-cache -r requirements/test.txt && \
  pip install --no-cache -r requirements/huggingface.txt && \
  pip install --no-cache -r requirements/dev.txt && \
  pip install --no-cache -r requirements/ingest-azure.txt && \
  pip install --no-cache -r requirements/ingest-github.txt && \
  pip install --no-cache -r requirements/ingest-gitlab.txt && \
  pip install --no-cache -r requirements/ingest-google-drive.txt && \
  pip install --no-cache -r requirements/ingest-reddit.txt && \
  pip install --no-cache -r requirements/ingest-s3.txt && \
  pip install --no-cache -r requirements/ingest-slack.txt && \
  pip install --no-cache -r requirements/ingest-wikipedia.txt && \
  pip install --no-cache -r requirements/local-inference.txt && \
  dnf -y groupremove "Development Tools" && \
  dnf clean all

RUN python3.8 -c "import nltk; nltk.download('punkt')" && \
  python3.8 -c "import nltk; nltk.download('averaged_perceptron_tagger')"

FROM deps as code

COPY example-docs example-docs
COPY unstructured unstructured

RUN python3.8 -c "from unstructured.ingest.doc_processor.generalized import initialize; initialize()"

CMD ["/bin/bash"]
