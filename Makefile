PACKAGE_NAME := unstructured
PIP_VERSION := 23.2.1
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
install: install-base-pip-packages install-dev install-nltk-models install-test install-huggingface install-all-docs

.PHONY: install-ci
install-ci: install-base-pip-packages install-nltk-models install-huggingface install-all-docs install-test install-pandoc

.PHONY: install-base-ci
install-base-ci: install-base-pip-packages install-nltk-models install-test install-pandoc

.PHONY: install-base-pip-packages
install-base-pip-packages:
	python3 -m pip install pip==${PIP_VERSION}
	python3 -m pip install -r requirements/base.txt

.PHONY: install-huggingface
install-huggingface:
	python3 -m pip install pip==${PIP_VERSION}
	python3 -m pip install -r requirements/huggingface.txt

.PHONY: install-nltk-models
install-nltk-models:
	python3 -c "from unstructured.nlp.tokenize import download_nltk_packages; download_nltk_packages()"

.PHONY: install-test
install-test:
	python3 -m pip install -r requirements/test.txt
	# NOTE(yao) - CI seem to always install tesseract to test so it would make sense to also require
	# pytesseract installation into the virtual env for testing
	python3 -m pip install unstructured_pytesseract
	# python3 -m pip install argilla==1.28.0 -c requirements/deps/constraints.txt
	# NOTE(robinson) - Installing weaviate-client separately here because the requests
	# version conflicts with label_studio_sdk
	python3 -m pip install weaviate-client -c requirements/deps/constraints.txt

.PHONY: install-dev
install-dev:
	python3 -m pip install -r requirements/dev.txt

.PHONY: install-build
install-build:
	python3 -m pip install -r requirements/build.txt

.PHONY: install-csv
install-csv:
	python3 -m pip install -r requirements/extra-csv.txt

.PHONY: install-docx
install-docx:
	python3 -m pip install -r requirements/extra-docx.txt

.PHONY: install-epub
install-epub:
	python3 -m pip install -r requirements/extra-epub.txt

.PHONY: install-odt
install-odt:
	python3 -m pip install -r requirements/extra-odt.txt

.PHONY: install-pypandoc
install-pypandoc:
	python3 -m pip install -r requirements/extra-pandoc.txt

.PHONY: install-markdown
install-markdown:
	python3 -m pip install -r requirements/extra-markdown.txt

.PHONY: install-pdf-image
install-pdf-image:
	python3 -m pip install -r requirements/extra-pdf-image.txt

.PHONY: install-pptx
install-pptx:
	python3 -m pip install -r requirements/extra-pptx.txt

.PHONY: install-xlsx
install-xlsx:
	python3 -m pip install -r requirements/extra-xlsx.txt

.PHONY: install-all-docs
install-all-docs: install-base install-csv install-docx install-epub install-odt install-pypandoc install-markdown install-pdf-image install-pptx install-xlsx


## install-local-inference: installs requirements for local inference
.PHONY: install-local-inference
install-local-inference: install install-all-docs

.PHONY: install-pandoc
install-pandoc:
	ARCH=${ARCH} ./scripts/install-pandoc.sh

## pip-compile:             compiles all base/dev/test requirements
.PHONY: pip-compile
pip-compile:
	@scripts/pip-compile.sh

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
export UNSTRUCTURED_INCLUDE_DEBUG_METADATA ?= false

## test:                    runs all unittests
.PHONY: test
test:
	PYTHONPATH=. CI=$(CI) \
	UNSTRUCTURED_INCLUDE_DEBUG_METADATA=$(UNSTRUCTURED_INCLUDE_DEBUG_METADATA) pytest test_${PACKAGE_NAME} -m "not chipper" --cov=${PACKAGE_NAME} --cov-report term-missing --durations=40

.PHONY: test-chipper
test-chipper:
	PYTHONPATH=. CI=$(CI) \
	UNSTRUCTURED_INCLUDE_DEBUG_METADATA=$(UNSTRUCTURED_INCLUDE_DEBUG_METADATA) pytest test_${PACKAGE_NAME} -m "chipper" --cov=${PACKAGE_NAME} --cov-report term-missing --durations=40

.PHONY: test-unstructured-api-unit
test-unstructured-api-unit:
	scripts/test-unstructured-api-unit.sh

.PHONY: test-no-extras
test-no-extras:
	PYTHONPATH=. CI=$(CI) \
		UNSTRUCTURED_INCLUDE_DEBUG_METADATA=$(UNSTRUCTURED_INCLUDE_DEBUG_METADATA) pytest \
		test_${PACKAGE_NAME}/partition/test_text.py \
		test_${PACKAGE_NAME}/partition/test_email.py \
		test_${PACKAGE_NAME}/partition/html/test_partition.py \
		test_${PACKAGE_NAME}/partition/test_xml_partition.py

.PHONY: test-extra-csv
test-extra-csv:
	PYTHONPATH=. CI=$(CI) pytest \
		test_unstructured/partition/test_csv.py \
		test_unstructured/partition/test_tsv.py

.PHONY: test-extra-docx
test-extra-docx:
	PYTHONPATH=. CI=$(CI) pytest \
		test_unstructured/partition/test_doc.py \
		test_unstructured/partition/test_docx.py

.PHONY: test-extra-epub
test-extra-epub:
	PYTHONPATH=. CI=$(CI) pytest test_unstructured/partition/test_epub.py

.PHONY: test-extra-markdown
test-extra-markdown:
	PYTHONPATH=. CI=$(CI) pytest test_unstructured/partition/test_md.py

.PHONY: test-extra-odt
test-extra-odt:
	PYTHONPATH=. CI=$(CI) pytest test_unstructured/partition/test_odt.py

.PHONY: test-extra-pdf-image
test-extra-pdf-image:
	PYTHONPATH=. CI=$(CI) pytest test_unstructured/partition/pdf_image

.PHONY: test-extra-pptx
test-extra-pptx:
	PYTHONPATH=. CI=$(CI) pytest \
		test_unstructured/partition/test_ppt.py \
		test_unstructured/partition/test_pptx.py

.PHONY: test-extra-pypandoc
test-extra-pypandoc:
	PYTHONPATH=. CI=$(CI) pytest \
		test_unstructured/partition/test_org.py \
		test_unstructured/partition/test_rst.py \
		test_unstructured/partition/test_rtf.py

.PHONY: test-extra-xlsx
test-extra-xlsx:
	PYTHONPATH=. CI=$(CI) pytest test_unstructured/partition/test_xlsx.py

## check:                   runs linters (includes tests)
.PHONY: check
check: check-ruff check-black check-flake8 check-version

.PHONY: check-shfmt
check-shfmt:
	shfmt -i 2 -d .

.PHONY: check-black
check-black:
	black . --check --line-length=100

.PHONY: check-flake8
check-flake8:
	flake8 .

.PHONY: check-licenses
check-licenses:
	@scripts/check-licenses.sh



.PHONY: check-ruff
check-ruff:
    # -- ruff options are determined by pyproject.toml --
	ruff check .

.PHONY: check-autoflake
check-autoflake:
	autoflake --check-diff .

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
tidy: tidy-python

.PHONY: tidy_shell
tidy-shell:
	shfmt -i 2 -l -w .

.PHONY: tidy-python
tidy-python:
	ruff . --fix-only || true
	autoflake --in-place .
	black --line-length=100 .

## version-sync:            update __version__.py with most recent version from CHANGELOG.md
.PHONY: version-sync
version-sync:
	scripts/version-sync.sh \
		-f "unstructured/__version__.py" semver

.PHONY: check-coverage
check-coverage:
	coverage report --fail-under=90

## check-deps:              check consistency of dependencies
.PHONY: check-deps
check-deps:
	scripts/consistent-deps.sh

.PHONY: check-extras
check-extras:
	scripts/check-extras.sh

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

.PHONY: docker-start-dev
docker-start-dev:
	docker run --rm \
	-v ${CURRENT_DIR}:/mnt/local_unstructued \
	-ti ${DOCKER_IMAGE}

.PHONY: docker-test
docker-test:
	docker run --rm \
	-v ${CURRENT_DIR}/test_unstructured:/home/notebook-user/test_unstructured \
	-v ${CURRENT_DIR}/test_unstructured_ingest:/home/notebook-user/test_unstructured_ingest \
	$(if $(wildcard uns_test_env_file),--env-file uns_test_env_file,) \
	$(DOCKER_IMAGE) \
	bash -c "CI=$(CI) \
	UNSTRUCTURED_INCLUDE_DEBUG_METADATA=$(UNSTRUCTURED_INCLUDE_DEBUG_METADATA) \
	pytest -m 'not chipper' $(if $(TEST_FILE),$(TEST_FILE),test_unstructured)"

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
