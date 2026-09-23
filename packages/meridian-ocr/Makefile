PACKAGE_NAME := unstructured_inference
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
	@uv sync --locked --all-groups

## install-lint:            install only lint dependencies (no project deps)
.PHONY: install-lint
install-lint:
	@uv sync --locked --only-group lint

## lock:                    update and lock all dependencies
.PHONY: lock
lock:
	@uv lock --upgrade

#################
# Test and Lint #
#################

export CI ?= false

## test:                    runs all unittests (excluding slow)
.PHONY: test
test:
	CI=$(CI) uv run --locked --no-sync pytest -n auto -m "not slow" test_${PACKAGE_NAME} --cov=${PACKAGE_NAME} --cov-report term-missing

## test-slow:               runs all unittests (including slow)
.PHONY: test-slow
test-slow:
	CI=$(CI) uv run --locked --no-sync pytest -n auto test_${PACKAGE_NAME} --cov=${PACKAGE_NAME} --cov-report term-missing

## check:                   runs all linters and checks
.PHONY: check
check: check-ruff check-version

## check-ruff:              runs ruff linter
.PHONY: check-ruff
check-ruff:
	uv run --locked --no-sync ruff check .
	uv run --locked --no-sync ruff format --check .

## check-scripts:           run shellcheck
.PHONY: check-scripts
check-scripts:
	scripts/shellcheck.sh

## check-version:           run check to ensure version in CHANGELOG.md matches version in package
.PHONY: check-version
check-version:
    # Fail if syncing version would produce changes
	scripts/version-sync.sh -c \
		-s CHANGELOG.md \
		-f ${PACKAGE_NAME}/__version__.py semver

## tidy:                    auto-format and fix lint issues
.PHONY: tidy
tidy:
	uv run --locked --no-sync ruff format .
	uv run --locked --no-sync ruff check --fix-only --show-fixes .

## version-sync:            update __version__.py with most recent version from CHANGELOG.md
.PHONY: version-sync
version-sync:
	scripts/version-sync.sh \
		-s CHANGELOG.md \
		-f ${PACKAGE_NAME}/__version__.py semver

## check-coverage:          check test coverage meets threshold
.PHONY: check-coverage
check-coverage:
	uv run --locked --no-sync coverage report --fail-under=90

##########
# Docker #
##########

DOCKER_IMAGE ?= unstructured-inference:dev

.PHONY: docker-build
docker-build:
	DOCKER_IMAGE=${DOCKER_IMAGE} ./scripts/docker-build.sh

.PHONY: docker-test
docker-test: docker-build
	docker run --rm \
	-v ${CURRENT_DIR}/test_unstructured_inference:/home/test_unstructured_inference \
	-v ${CURRENT_DIR}/sample-docs:/home/sample-docs \
	$(DOCKER_IMAGE) \
	bash -c "pytest -n auto $(if $(TEST_NAME),-k $(TEST_NAME),) test_unstructured_inference"
