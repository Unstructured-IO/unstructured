# syntax=docker/dockerfile:experimental
FROM quay.io/unstructured-io/base-images:rocky9.2-8@sha256:68b11677eab35ea702cfa682202ddae33f2053ea16c14c951120781a2dcac1b2 as base

# NOTE(crag): NB_USER ARG for mybinder.org compat:
#             https://mybinder.readthedocs.io/en/latest/tutorials/dockerfile.html
ARG NB_USER=notebook-user
ARG NB_UID=1000
ARG PIP_VERSION

# Set up environment
ENV HOME /home/${NB_USER}
ENV PYTHONPATH="${PYTHONPATH}:${HOME}"
ENV PATH="/home/usr/.local/bin:${PATH}"

RUN groupadd --gid ${NB_UID} ${NB_USER}
RUN useradd --uid ${NB_UID} --gid ${NB_UID} ${NB_USER}
WORKDIR ${HOME}
RUN mkdir ${HOME}/.ssh && chmod go-rwx ${HOME}/.ssh \
  &&  ssh-keyscan -t rsa github.com >> ${HOME}/.ssh/known_hosts

FROM base as deps
# Copy and install Unstructured
COPY requirements requirements

RUN python3.10 -m pip install pip==${PIP_VERSION} && \
  dnf -y groupinstall "Development Tools" && \
  find requirements/ -type f -name "*.txt" -exec python3 -m pip install --no-cache -r '{}' ';' && \
  dnf -y groupremove "Development Tools" && \
  dnf clean all

RUN python3.10 -c "import nltk; nltk.download('punkt')" && \
  python3.10 -c "import nltk; nltk.download('averaged_perceptron_tagger')"

FROM deps as code

USER ${NB_USER}

COPY example-docs example-docs
COPY unstructured unstructured

RUN python3.10 -c "from unstructured.ingest.pipeline.initialize import initialize; initialize()"

CMD ["/bin/bash"]
