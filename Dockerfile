# syntax=docker/dockerfile:experimental

FROM centos:centos7.9.2009

ARG PIP_VERSION
ARG UNSTRUCTURED

RUN yum -y update && \
  yum -y install poppler-utils xz-devel wget tar curl make which

# Enable the EPEL repository
RUN yum install -y epel-release && yum clean all

# Install pandoc
RUN yum install -y pandoc && yum clean all

# # Install compilers
# RUN yum install -y centos-release-scl && \
#     yum install -y devtoolset-9-gcc devtoolset-9-gcc-c++ wget tar curl make xz-devel && \
#     scl enable devtoolset-9 -- sh -c 'echo "source /opt/rh/devtoolset-9/enable" >> /etc/profile.d/devtoolset-9.sh'

# Note(yuming): Install gcc & g++ ≥ 5.4 for Detectron2 and Tesseract requirement
RUN yum -y update
RUN yum -y install centos-release-scl
RUN yum -y install devtoolset-7-gcc*
SHELL [ "/usr/bin/scl", "enable", "devtoolset-7"]

# Install Tessaract
RUN set -ex && \
    pac="yum" && \
    $sudo "$pac" install -y opencv opencv-devel opencv-python perl-core clang libpng-devel libtiff-devel libwebp-devel libjpeg-turbo-devel git-core libtool pkgconfig xz && \
    wget https://github.com/DanBloomberg/leptonica/releases/download/1.75.1/leptonica-1.75.1.tar.gz && \
    tar -xzvf leptonica-1.75.1.tar.gz && \
    cd leptonica-1.75.1 || exit && \
    ./configure && make && $sudo make install && \
    cd .. && \
    wget http://mirror.squ.edu.om/gnu/autoconf-archive/autoconf-archive-2017.09.28.tar.xz && \
    tar -xvf autoconf-archive-2017.09.28.tar.xz && \
    cd autoconf-archive-2017.09.28 || exit && \
    ./configure && make && $sudo make install && \
    $sudo cp m4/* /usr/share/aclocal && \
    cd .. && \
    git clone --depth 1  https://github.com/tesseract-ocr/tesseract.git tesseract-ocr && \
    cd tesseract-ocr || exit && \
    export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig && \
    scl enable devtoolset-9 -- sh -c './autogen.sh && ./configure && make && make install' && \
    cd .. && \
    git clone https://github.com/tesseract-ocr/tessdata.git && \
    $sudo cp tessdata/*.traineddata /usr/local/share/tessdata

# Install 
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
