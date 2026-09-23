PARTITION_DIR := packages/meridian-partition
CURRENT_DIR := $(shell pwd)

.PHONY: help
help: Makefile
	@sed -n 's/^\(## \)\([a-zA-Z]\)/\2/p' $<


###########
# Install #
###########

## install:                 install all workspace packages, extras and dependency groups
.PHONY: install
install:
	@uv sync --locked --all-packages --all-extras --all-groups

## lock:                    update and lock all workspace dependencies
.PHONY: lock
lock:
	@uv lock --upgrade


#################
# Test and Lint #
#################

## test:                    run the test suites of all packages
.PHONY: test
test: test-partition

## test-partition:          run the meridian_partition test suite
.PHONY: test-partition
test-partition:
	$(MAKE) -C $(PARTITION_DIR) test

## check:                   run linters and version checks for all packages
.PHONY: check
check: check-partition

## check-partition:         run linters and version checks for meridian_partition
.PHONY: check-partition
check-partition:
	$(MAKE) -C $(PARTITION_DIR) check

## tidy:                    auto-format and fix lint issues in all packages
.PHONY: tidy
tidy:
	$(MAKE) -C $(PARTITION_DIR) tidy

## tidy-shell:              format all shell scripts in the repository
.PHONY: tidy-shell
tidy-shell:
	shfmt -i 2 -l -w .


##########
# Docker #
##########

# Docker targets are provided for convenience only and are not required in a standard development environment

DOCKER_IMAGE ?= meridian_partition:dev
export CI ?= false
export MERIDIAN_PARTITION_INCLUDE_DEBUG_METADATA ?= false

.PHONY: docker-build
docker-build:
	DOCKER_IMAGE=${DOCKER_IMAGE} ./$(PARTITION_DIR)/scripts/docker-build.sh

.PHONY: docker-start-bash
docker-start-bash:
	docker run -ti --rm ${DOCKER_IMAGE}

.PHONY: docker-start-dev
docker-start-dev:
	docker run --rm \
	-v ${CURRENT_DIR}:/mnt/local_meridian_partition \
	-ti ${DOCKER_IMAGE}

.PHONY: docker-test
docker-test:
	docker run --rm \
	-v ${CURRENT_DIR}/$(PARTITION_DIR)/test_meridian_partition:/home/notebook-user/test_meridian_partition \
	-v ${CURRENT_DIR}/$(PARTITION_DIR)/test_unstructured_ingest:/home/notebook-user/test_unstructured_ingest \
	$(if $(wildcard uns_test_env_file),--env-file uns_test_env_file,) \
	--env DO_NOT_TRACK=1 \
	$(DOCKER_IMAGE) \
	bash -c "uv sync --locked --all-packages --all-extras --group test --no-install-workspace && \
	cd $(PARTITION_DIR) && \
	CI=$(CI) \
	MERIDIAN_PARTITION_INCLUDE_DEBUG_METADATA=$(MERIDIAN_PARTITION_INCLUDE_DEBUG_METADATA) \
	uv run --no-sync pytest -n auto $(if $(TEST_FILE),$(TEST_FILE),test_meridian_partition)"

.PHONY: docker-smoke-test
docker-smoke-test:
	DOCKER_IMAGE=${DOCKER_IMAGE} ./$(PARTITION_DIR)/scripts/docker-smoke-test.sh


###########
# Jupyter #
###########

.PHONY: docker-jupyter-notebook
docker-jupyter-notebook:
	docker run -p 8888:8888 --mount type=bind,source=$(realpath .),target=/home --entrypoint jupyter-notebook -t --rm ${DOCKER_IMAGE} --allow-root --port 8888 --ip 0.0.0.0 --NotebookApp.token='' --NotebookApp.password=''


.PHONY: run-jupyter
run-jupyter:
	uv run --no-sync jupyter-notebook --NotebookApp.token='' --NotebookApp.password=''
