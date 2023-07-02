PACKAGE_NAME := unstructured
PIP_VERSION := 23.1.2
CURRENT_DIR := $(shell pwd)
ARCH := $(shell uname -m)

.PHONY: help
help: Makefile
	@sed -n 's/^\(## \)\([a-zA-Z]\)/\2/p' $<


###########
# Install #
###########

## install-base:            installs core requirements needed for text processing bricks
.PHONY: install-base
install-base: install-base-pip-packages install-nltk-models

## install:                 installs all test, dev, and experimental requirements
.PHONY: install
install: install-base-pip-packages install-dev install-nltk-models install-test install-huggingface install-unstructured-inference

.PHONY: install-ci
install-ci: install-base-pip-packages install-nltk-models install-huggingface install-unstructured-inference install-test

.PHONY: install-base-pip-packages
install-base-pip-packages:
	python3 -m pip install pip==${PIP_VERSION}
	python3 -m pip install -r requirements/base.txt

.PHONY: install-huggingface
install-huggingface:
	python3 -m pip install pip==${PIP_VERSION}
	python3 -m pip install -r requirements/huggingface.txt

.PHONE: install-nltk-models
install-nltk-models:
	python -c "import nltk; nltk.download('punkt')"
	python -c "import nltk; nltk.download('averaged_perceptron_tagger')"

.PHONY: install-test
install-test:
	python3 -m pip install -r requirements/test.txt
	# NOTE(robinson) - Installing weaviate-client separately here because the requests
	# version conflicts with label_studio_sdk
	python3 -m pip install weaviate-client

.PHONY: install-dev
install-dev:
	python3 -m pip install -r requirements/dev.txt

.PHONY: install-build
install-build:
	python3 -m pip install -r requirements/build.txt

.PHONY: install-ingest-google-drive
install-ingest-google-drive:
	python3 -m pip install -r requirements/ingest-google-drive.txt

## install-ingest-s3:       install requirements for the s3 connector
.PHONY: install-ingest-s3
install-ingest-s3:
	python3 -m pip install -r requirements/ingest-s3.txt

.PHONY: install-ingest-gcs
install-ingest-gcs:
	python3 -m pip install -r requirements/ingest-gcs.txt

.PHONY: install-ingest-dropbox
install-ingest-dropbox:
	python3 -m pip install -r requirements/ingest-dropbox.txt

.PHONY: install-ingest-azure
install-ingest-azure:
	python3 -m pip install -r requirements/ingest-azure.txt

.PHONY: install-ingest-discord
install-ingest-discord:
	pip install -r requirements/ingest-discord.txt

.PHONY: install-ingest-github
install-ingest-github:
	python3 -m pip install -r requirements/ingest-github.txt

.PHONY: install-ingest-gitlab
install-ingest-gitlab:
	python3 -m pip install -r requirements/ingest-gitlab.txt

.PHONY: install-ingest-reddit
install-ingest-reddit:
	python3 -m pip install -r requirements/ingest-reddit.txt

.PHONY: install-ingest-slack
install-ingest-slack:
	pip install -r requirements/ingest-slack.txt

.PHONY: install-ingest-wikipedia
install-ingest-wikipedia:
	python3 -m pip install -r requirements/ingest-wikipedia.txt

.PHONY: install-ingest-elasticsearch
install-ingest-elasticsearch:
	python3 -m pip install -r requirements/ingest-elasticsearch.txt
.PHONY: install-unstructured-inference
install-unstructured-inference:
	python3 -m pip install -r requirements/local-inference.txt

## install-local-inference: installs requirements for local inference
.PHONY: install-local-inference
install-local-inference: install install-unstructured-inference

.PHONY: install-pandoc
install-pandoc:
	ARCH=${ARCH} ./scripts/install-pandoc.sh


## pip-compile:             compiles all base/dev/test requirements
.PHONY: pip-compile
pip-compile:
	pip-compile --upgrade requirements/base.in
	# Extra requirements for huggingface staging functions
	pip-compile --upgrade requirements/huggingface.in
	pip-compile --upgrade requirements/test.in
	pip-compile --upgrade requirements/dev.in
	pip-compile --upgrade requirements/build.in
	pip-compile --upgrade requirements/local-inference.in
	# NOTE(robinson) - doc/requirements.txt is where the GitHub action for building
	# sphinx docs looks for additional requirements
	cp requirements/build.txt docs/requirements.txt
	pip-compile --upgrade requirements/ingest-s3.in
	pip-compile --upgrade requirements/ingest-gcs.in
	pip-compile --upgrade requirements/ingest-dropbox.in
	pip-compile --upgrade requirements/ingest-azure.in
	pip-compile --upgrade requirements/ingest-discord.in
	pip-compile --upgrade requirements/ingest-reddit.in
	pip-compile --upgrade requirements/ingest-github.in
	pip-compile --upgrade requirements/ingest-gitlab.in
	pip-compile --upgrade requirements/ingest-slack.in
	pip-compile --upgrade requirements/ingest-wikipedia.in
	pip-compile --upgrade requirements/ingest-google-drive.in
	pip-compile --upgrade requirements/ingest-elasticsearch.in

## install-project-local:   install unstructured into your local python environment
.PHONY: install-project-local
install-project-local: install
	# MAYBE TODO: fail if already exists?
	pip install -e .

## uninstall-project-local: uninstall unstructured from your local python environment
.PHONY: uninstall-project-local
uninstall-project-local:
	pip uninstall ${PACKAGE_NAME}

#################
# Test and Lint #
#################

export CI ?= false

## test:                    runs all unittests
.PHONY: test
test:
	PYTHONPATH=. CI=$(CI) pytest test_${PACKAGE_NAME} --cov=${PACKAGE_NAME} --cov-report term-missing

## check:                   runs linters (includes tests)
.PHONY: check
check: check-src check-tests check-version

## check-src:               runs linters (source only, no tests)
.PHONY: check-src
check-src:
	ruff . --select I,UP015,UP032,UP034,UP018,COM,C4,PT,SIM,PLR0402 --ignore PT011,PT012,SIM117
	black --line-length 100 ${PACKAGE_NAME} --check
	flake8 ${PACKAGE_NAME}
	mypy ${PACKAGE_NAME} --ignore-missing-imports --check-untyped-defs

.PHONY: check-tests
check-tests:
	black --line-length 100 test_${PACKAGE_NAME} --check
	flake8 test_${PACKAGE_NAME}

## check-scripts:           run shellcheck
.PHONY: check-scripts
check-scripts:
    # Fail if any of these files have warnings
	scripts/shellcheck.sh

## check-version:           run check to ensure version in CHANGELOG.md matches version in package
.PHONY: check-version
check-version:
    # Fail if syncing version would produce changes
	scripts/version-sync.sh -c \
		-f "unstructured/__version__.py" semver

## tidy:                    run black
.PHONY: tidy
tidy:
	ruff . --select I,UP015,UP032,UP034,UP018,COM,C4,PT,SIM,PLR0402 --fix-only || true
	black --line-length 100 ${PACKAGE_NAME}
	black --line-length 100 test_${PACKAGE_NAME}

## version-sync:            update __version__.py with most recent version from CHANGELOG.md
.PHONY: version-sync
version-sync:
	scripts/version-sync.sh \
		-f "unstructured/__version__.py" semver

.PHONY: check-coverage
check-coverage:
	coverage report --fail-under=95

## check-deps:              check consistency of dependencies
.PHONY: check-deps
check-deps:
	scripts/consistent-deps.sh

##########
# Docker #
##########

# Docker targets are provided for convenience only and are not required in a standard development environment

DOCKER_IMAGE ?= unstructured:dev

.PHONY: docker-build
docker-build:
	PIP_VERSION=${PIP_VERSION} DOCKER_IMAGE_NAME=${DOCKER_IMAGE} ./scripts/docker-build.sh

.PHONY: docker-start-bash
docker-start-bash:
	docker run -ti --rm ${DOCKER_IMAGE}

.PHONY: docker-test
docker-test:
	docker run --rm \
	-v ${CURRENT_DIR}/test_unstructured:/home/test_unstructured \
	-v ${CURRENT_DIR}/test_unstructured_ingest:/home/test_unstructured_ingest \
	$(if $(wildcard uns_test_env_file),--env-file uns_test_env_file,) \
	$(DOCKER_IMAGE) \
	bash -c "CI=$(CI) pytest $(if $(TEST_NAME),-k $(TEST_NAME),) test_unstructured"

.PHONY: docker-smoke-test
docker-smoke-test:
	DOCKER_IMAGE=${DOCKER_IMAGE} ./scripts/docker-smoke-test.sh


###########
# Jupyter #
###########

.PHONY: docker-jupyter-notebook
docker-jupyter-notebook:
	docker run -p 8888:8888 --mount type=bind,source=$(realpath .),target=/home --entrypoint jupyter-notebook -t --rm ${DOCKER_IMAGE} --allow-root --port 8888 --ip 0.0.0.0 --NotebookApp.token='' --NotebookApp.password=''


.PHONY: run-jupyter
run-jupyter:
	PYTHONPATH=$(realpath .) JUPYTER_PATH=$(realpath .) jupyter-notebook --NotebookApp.token='' --NotebookApp.password=''
