# Unstructed Installation Instructions from https://github.com/Unstructured-IO/unstructured#coffee-installation-instructions-for-local-development
FROM mcr.microsoft.com/devcontainers/python:0-3.8

# https://github.com/Unstructured-IO/community#linux
RUN git clone https://github.com/pyenv/pyenv.git ~/.pyenv
RUN git clone https://github.com/pyenv/pyenv-virtualenv.git ~/.pyenv/plugins/pyenv-virtualenv

# https://github.com/pyenv/pyenv#user-content-set-up-your-shell-environment-for-pyenv
WORKDIR /root/unstructured
COPY . /root/unstructured

ENV HOME="/root/unstructured"
ENV PYENV_ROOT="${HOME}/.pyenv"

ENV PATH="/root/.pyenv/bin:${PATH}"
ENV PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${PATH}"
RUN eval "$(pyenv init -)" && \
    pyenv install 3.8.15 && \
    pyenv virtualenv 3.8.15 unstructured && \
    pyenv activate unstructured && \
    ls -la && \
    make install && \
    make install-local-inference

RUN echo 'eval "$(pyenv init -)"' >> ~/.bashrc
RUN echo 'source $HOME/.pyenv/versions/unstructured/bin/activate' >> ~/.bashrc
