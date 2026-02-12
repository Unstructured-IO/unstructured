PACKAGE_NAME := unstructured
CURRENT_DIR := $(shell pwd)

.PHONY: help
help: Makefile
	@sed -n 's/^\(## \)\([a-zA-Z]\)/\2/p' $<


###########
# Install #
###########

## install:                 install all dependencies via uv
.PHONY: install
install:
	@uv sync --locked --all-extras --all-groups
	@$(MAKE) install-nltk-models

## lock:                    update and lock all dependencies
.PHONY: lock
lock:
	@uv lock --upgrade

.PHONY: install-nltk-models
install-nltk-models:
	uv run --no-sync python -c "from unstructured.nlp.tokenize import download_nltk_packages; download_nltk_packages()"


#################
# Test and Lint #
#################

export CI ?= false
export UNSTRUCTURED_INCLUDE_DEBUG_METADATA ?= false

## test:                    runs all unittests
.PHONY: test
test:
	CI=$(CI) \
	UNSTRUCTURED_INCLUDE_DEBUG_METADATA=$(UNSTRUCTURED_INCLUDE_DEBUG_METADATA) \
	uv run --no-sync pytest -n auto test_${PACKAGE_NAME} --cov=${PACKAGE_NAME} --cov-report term-missing --durations=40

.PHONY: test-no-extras
test-no-extras:
	CI=$(CI) \
	UNSTRUCTURED_INCLUDE_DEBUG_METADATA=$(UNSTRUCTURED_INCLUDE_DEBUG_METADATA) \
	uv run --no-sync pytest -n auto \
		test_${PACKAGE_NAME}/partition/test_text.py \
		test_${PACKAGE_NAME}/partition/test_email.py \
		test_${PACKAGE_NAME}/partition/html/test_partition.py \
		test_${PACKAGE_NAME}/partition/test_xml.py

.PHONY: test-extra-csv
test-extra-csv:
	CI=$(CI) uv run --no-sync pytest -n auto \
		test_unstructured/partition/test_csv.py \
		test_unstructured/partition/test_tsv.py

.PHONY: test-extra-docx
test-extra-docx:
	CI=$(CI) uv run --no-sync pytest -n auto \
		test_unstructured/partition/test_doc.py \
		test_unstructured/partition/test_docx.py

.PHONY: test-extra-epub
test-extra-epub:
	CI=$(CI) uv run --no-sync pytest -n auto test_unstructured/partition/test_epub.py

.PHONY: test-extra-markdown
test-extra-markdown:
	CI=$(CI) uv run --no-sync pytest -n auto test_unstructured/partition/test_md.py

.PHONY: test-extra-odt
test-extra-odt:
	CI=$(CI) uv run --no-sync pytest -n auto test_unstructured/partition/test_odt.py

.PHONY: test-extra-pdf-image
test-extra-pdf-image:
	CI=$(CI) uv run --no-sync pytest -n auto test_unstructured/partition/pdf_image

.PHONY: test-extra-pptx
test-extra-pptx:
	CI=$(CI) uv run --no-sync pytest -n auto \
		test_unstructured/partition/test_ppt.py \
		test_unstructured/partition/test_pptx.py

.PHONY: test-extra-pypandoc
test-extra-pypandoc:
	CI=$(CI) uv run --no-sync pytest -n auto \
		test_unstructured/partition/test_org.py \
		test_unstructured/partition/test_rst.py \
		test_unstructured/partition/test_rtf.py

.PHONY: test-extra-xlsx
test-extra-xlsx:
	CI=$(CI) uv run --no-sync pytest -n auto test_unstructured/partition/test_xlsx.py

## check:                   runs all linters and checks
.PHONY: check
check: check-ruff check-version

## check-ruff:              runs ruff linter and formatter check
.PHONY: check-ruff
check-ruff:
	uv run --no-sync ruff check .
	uv run --no-sync ruff format --check .

.PHONY: check-licenses
check-licenses:
	@scripts/check-licenses.sh

## check-version:           run check to ensure version in CHANGELOG.md matches version in package
.PHONY: check-version
check-version:
    # Fail if syncing version would produce changes
	scripts/version-sync.sh -c \
		-f "unstructured/__version__.py" semver

## tidy:                    auto-format and fix lint issues
.PHONY: tidy
tidy:
	uv run --no-sync ruff format .
	uv run --no-sync ruff check --fix-only --show-fixes .

.PHONY: tidy-shell
tidy-shell:
	shfmt -i 2 -l -w .

## version-sync:            update __version__.py with most recent version from CHANGELOG.md
.PHONY: version-sync
version-sync:
	scripts/version-sync.sh \
		-f "unstructured/__version__.py" semver

## check-coverage:          check test coverage meets threshold
.PHONY: check-coverage
check-coverage:
	uv run --no-sync coverage report --fail-under=90

##########
# Docker #
##########

# Docker targets are provided for convenience only and are not required in a standard development environment

DOCKER_IMAGE ?= unstructured:dev

.PHONY: docker-build
docker-build:
	DOCKER_IMAGE=${DOCKER_IMAGE} ./scripts/docker-build.sh

.PHONY: docker-start-bash
docker-start-bash:
	docker run -ti --rm ${DOCKER_IMAGE}

.PHONY: docker-start-dev
docker-start-dev:
	docker run --rm \
	-v ${CURRENT_DIR}:/mnt/local_unstructured \
	-ti ${DOCKER_IMAGE}

.PHONY: docker-test
docker-test:
	docker run --rm \
	-v ${CURRENT_DIR}/test_unstructured:/home/notebook-user/test_unstructured \
	-v ${CURRENT_DIR}/test_unstructured_ingest:/home/notebook-user/test_unstructured_ingest \
	$(if $(wildcard uns_test_env_file),--env-file uns_test_env_file,) \
	$(DOCKER_IMAGE) \
	bash -c "uv sync --locked --all-extras --group test --no-install-project && \
	CI=$(CI) \
	UNSTRUCTURED_INCLUDE_DEBUG_METADATA=$(UNSTRUCTURED_INCLUDE_DEBUG_METADATA) \
	uv run --no-sync pytest -n auto $(if $(TEST_FILE),$(TEST_FILE),test_unstructured)"

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
	uv run --no-sync jupyter-notebook --NotebookApp.token='' --NotebookApp.password=''


###########
# Other #
###########

.PHONY: html-fixtures-update
html-fixtures-update:
	rm -r test_unstructured_ingest/expected-structured-output-html && \
	uv run --no-sync test_unstructured_ingest/structured-json-to-html.sh test_unstructured_ingest/expected-structured-output-html

.PHONY: markdown-fixtures-update
markdown-fixtures-update:
	rm -r test_unstructured_ingest/expected-structured-output-markdown && \
	uv run --no-sync test_unstructured_ingest/structured-json-to-markdown.sh test_unstructured_ingest/expected-structured-output-markdown
