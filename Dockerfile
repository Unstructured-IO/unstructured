# syntax=docker/dockerfile:experimental

FROM centos:centos7.9.2009

ARG PIP_VERSION
ARG UNSTRUCTURED

RUN yum -y update && \
  yum -y install poppler-utils xz-devel which

# Enable the EPEL repository
RUN yum install -y epel-release && yum clean all

# Install pandoc
RUN yum install -y pandoc && yum clean all

# Note(austin) Get a recent tesseract from this repo
# See https://tesseract-ocr.github.io/tessdoc/Installation.html
# PDF and images:
RUN yum-config-manager --add-repo https://download.opensuse.org/repositories/home:/Alexander_Pozdnyakov/CentOS_7/ && \
  rpm --import https://build.opensuse.org/projects/home:Alexander_Pozdnyakov/public_key && \
  yum -y update && \
  yum -y install tesseract

# Note(yuming): Install gcc & g++ ≥ 5.4 for Detectron2 requirement
RUN yum -y update
RUN yum -y install centos-release-scl
RUN yum -y install devtoolset-7-gcc*
SHELL [ "/usr/bin/scl", "enable", "devtoolset-7"]

RUN yum -y update && \
  # MS Office docs:
  yum -y install libreoffice && \
  yum -y install openssl-devel bzip2-devel libffi-devel make git sqlite-devel && \
  curl -O https://www.python.org/ftp/python/3.8.15/Python-3.8.15.tgz && tar -xzf Python-3.8.15.tgz && \
  cd Python-3.8.15/ && ./configure --enable-optimizations && make altinstall && \
  cd .. && rm -rf Python-3.8.15* && \
  ln -s /usr/local/bin/python3.8 /usr/local/bin/python3

# create a home directory
ENV HOME /home/

WORKDIR ${HOME}
RUN mkdir ${HOME}/.ssh && chmod go-rwx ${HOME}/.ssh \
  &&  ssh-keyscan -t rsa github.com >> /home/.ssh/known_hosts

ENV PYTHONPATH="${PYTHONPATH}:${HOME}"
ENV PATH="/home/usr/.local/bin:${PATH}"

COPY example-docs example-docs

COPY requirements/base.txt requirements-base.txt
COPY requirements/test.txt requirements-test.txt
COPY requirements/huggingface.txt requirements-huggingface.txt
COPY requirements/dev.txt requirements-dev.txt
# PDFs and images
COPY requirements/local-inference.txt requirements-local-inference.txt


RUN python3.8 -m pip install pip==${PIP_VERSION} \
  && pip install --no-cache -r requirements-base.txt \
  && pip install --no-cache -r requirements-test.txt \
  && pip install --no-cache -r requirements-huggingface.txt \
  && pip install --no-cache -r requirements-dev.txt \
  # PDFs and images
  && pip install --no-cache -r requirements-local-inference.txt \
  # PDFs
  && pip install --no-cache "detectron2@git+https://github.com/facebookresearch/detectron2.git@v0.6#egg=detectron2"

COPY unstructured unstructured

CMD ["/bin/bash"]
