PACKAGE_NAME := unstructured
CURRENT_DIR := $(shell pwd)
ARCH := $(shell uname -m)
PYTHON ?= python3

.PHONY: help
help: Makefile
	@sed -n 's/^\(## \)\([a-zA-Z]\)/\2/p' $<

.PHONY: install-uv
install-uv:
	@uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh

###########
# Install #
###########

.PHONY: install-dependencies
install-dependencies:
	@uv sync --all-groups

.PHONY: upgrade-dependencies
upgrade-dependencies:
	@uv sync --all-groups --upgrade

.PHONY: install
install:
	install-uv install-dependencies

#########
# Tests #
#########

export CI ?= false
export UNSTRUCTURED_INCLUDE_DEBUG_METADATA ?= false

.PHONY: test
test:
	CI=$(CI) UNSTRUCTURED_INCLUDE_DEBUG_METADATA=$(UNSTRUCTURED_INCLUDE_DEBUG_METADATA) \
	uv run pytest test_$(PACKAGE_NAME) --cov=$(PACKAGE_NAME) --cov-report term-missing --durations=40

.PHONY: test-unstructured-api-unit
test-unstructured-api-unit:
	scripts/test-unstructured-api-unit.sh

.PHONY: test-no-extras
test-no-extras:
	CI=$(CI) UNSTRUCTURED_INCLUDE_DEBUG_METADATA=$(UNSTRUCTURED_INCLUDE_DEBUG_METADATA) \
	uv run pytest \
		test_$(PACKAGE_NAME)/partition/test_text.py \
		test_$(PACKAGE_NAME)/partition/test_email.py \
		test_$(PACKAGE_NAME)/partition/html/test_partition.py \
		test_$(PACKAGE_NAME)/partition/test_xml.py

.PHONY: test-extra-csv
test-extra-csv:
	CI=$(CI) uv run pytest \
		test_unstructured/partition/test_csv.py \
		test_unstructured/partition/test_tsv.py

.PHONY: test-extra-docx
test-extra-docx:
	CI=$(CI) uv run pytest \
		test_unstructured/partition/test_doc.py \
		test_unstructured/partition/test_docx.py

.PHONY: test-extra-epub
test-extra-epub:
	CI=$(CI) uv run pytest test_unstructured/partition/test_epub.py

.PHONY: test-extra-markdown
test-extra-markdown:
	CI=$(CI) uv run pytest test_unstructured/partition/test_md.py

.PHONY: test-extra-odt
test-extra-odt:
	CI=$(CI) uv run pytest test_unstructured/partition/test_odt.py

.PHONY: test-extra-pdf-image
test-extra-pdf-image:
	CI=$(CI) uv run pytest test_unstructured/partition/pdf_image

.PHONY: test-extra-pptx
test-extra-pptx:
	CI=$(CI) uv run pytest \
		test_unstructured/partition/test_ppt.py \
		test_unstructured/partition/test_pptx.py

.PHONY: test-extra-pypandoc
test-extra-pypandoc:
	CI=$(CI) uv run pytest \
		test_unstructured/partition/test_org.py \
		test_unstructured/partition/test_rst.py \
		test_unstructured/partition/test_rtf.py

.PHONY: test-extra-xlsx
test-extra-xlsx:
	CI=$(CI) uv run pytest test_unstructured/partition/test_xlsx.py

.PHONY: test-text-extraction-evaluate
test-text-extraction-evaluate:
	CI=$(CI) uv run pytest test_unstructured/metrics/test_text_extraction.py


###########
#  CHECK  #
###########

.PHONY: check
check: check-ruff check-yaml check-docker

.PHONY: check-ruff
check-ruff:
	uv run ruff check .

.PHONY: check-yaml
check-yaml:
	uv run yamllint .

.PHONY: check-docker
check-docker:
	uv run hadolint Dockerfile

.PHONY: check-licenses
check-licenses:
	@scripts/check-licenses.sh

.PHONY: check-scripts
check-scripts:
    # Fail if any of these files have warnings
	scripts/shellcheck.sh

###########
#  TIDY   #
###########

.PHONY: tidy
tidy: tidy-ruff

.PHONY: tidy-ruff
tidy-ruff:
	uv run ruff format .
	uv run ruff check --fix-only --show-fixes .

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
	bash -c "pip install -r requirements/test.txt -r requirements/dev.txt && \
	CI=$(CI) \
	UNSTRUCTURED_INCLUDE_DEBUG_METADATA=$(UNSTRUCTURED_INCLUDE_DEBUG_METADATA) \
	python3 -m pytest $(if $(TEST_FILE),$(TEST_FILE),test_unstructured)"

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


###########
# Other #
###########

.PHONY: html-fixtures-update
html-fixtures-update:
	rm -r test_unstructured_ingest/expected-structured-output-html && \
	test_unstructured_ingest/structured-json-to-html.sh test_unstructured_ingest/expected-structured-output-html
