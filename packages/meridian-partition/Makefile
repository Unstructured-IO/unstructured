PACKAGE_NAME := meridian_partition

.PHONY: help
help: Makefile
	@sed -n 's/^\(## \)\([a-zA-Z]\)/\2/p' $<


###########
# Install #
###########

## install:                 install this package with all extras and dependency groups via uv
.PHONY: install
install:
	@uv sync --locked --all-extras --all-groups

## lock:                    update and lock all workspace dependencies
.PHONY: lock
lock:
	@uv lock --upgrade


#################
# Test and Lint #
#################

export CI ?= false
export MERIDIAN_PARTITION_INCLUDE_DEBUG_METADATA ?= false

## test:                    runs all unittests
.PHONY: test
test:
	CI=$(CI) \
	MERIDIAN_PARTITION_INCLUDE_DEBUG_METADATA=$(MERIDIAN_PARTITION_INCLUDE_DEBUG_METADATA) \
	uv run --no-sync pytest -n auto test_${PACKAGE_NAME} --cov=${PACKAGE_NAME} --cov-report term-missing --durations=40

.PHONY: test-no-extras
test-no-extras:
	CI=$(CI) \
	MERIDIAN_PARTITION_INCLUDE_DEBUG_METADATA=$(MERIDIAN_PARTITION_INCLUDE_DEBUG_METADATA) \
	uv run --no-sync pytest -n auto \
		test_${PACKAGE_NAME}/partition/test_text.py \
		test_${PACKAGE_NAME}/partition/test_email.py \
		test_${PACKAGE_NAME}/partition/html/test_partition.py \
		test_${PACKAGE_NAME}/partition/test_xml.py

.PHONY: test-extra-csv
test-extra-csv:
	CI=$(CI) uv run --no-sync pytest -n auto \
		test_meridian_partition/partition/test_csv.py \
		test_meridian_partition/partition/test_tsv.py

.PHONY: test-extra-docx
test-extra-docx:
	CI=$(CI) uv run --no-sync pytest -n auto \
		test_meridian_partition/partition/test_doc.py \
		test_meridian_partition/partition/test_docx.py

.PHONY: test-extra-epub
test-extra-epub:
	CI=$(CI) uv run --no-sync pytest -n auto test_meridian_partition/partition/test_epub.py

.PHONY: test-extra-markdown
test-extra-markdown:
	CI=$(CI) uv run --no-sync pytest -n auto test_meridian_partition/partition/test_md.py

.PHONY: test-extra-odt
test-extra-odt:
	CI=$(CI) uv run --no-sync pytest -n auto test_meridian_partition/partition/test_odt.py

.PHONY: test-extra-pdf-image
test-extra-pdf-image:
	CI=$(CI) uv run --no-sync pytest -n auto test_meridian_partition/partition/pdf_image

.PHONY: test-extra-pptx
test-extra-pptx:
	CI=$(CI) uv run --no-sync pytest -n auto \
		test_meridian_partition/partition/test_ppt.py \
		test_meridian_partition/partition/test_pptx.py

.PHONY: test-extra-pypandoc
test-extra-pypandoc:
	CI=$(CI) uv run --no-sync pytest -n auto \
		test_meridian_partition/partition/test_org.py \
		test_meridian_partition/partition/test_rst.py \
		test_meridian_partition/partition/test_rtf.py

.PHONY: test-extra-xlsx
test-extra-xlsx:
	CI=$(CI) uv run --no-sync pytest -n auto test_meridian_partition/partition/test_xlsx.py

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
		-f "meridian_partition/__version__.py" semver

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
		-f "meridian_partition/__version__.py" semver

## check-coverage:          check test coverage meets threshold
.PHONY: check-coverage
check-coverage:
	uv run --no-sync coverage report --fail-under=90

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
