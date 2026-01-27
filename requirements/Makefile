SHELL := /bin/bash

BASE_REQUIREMENTS := $(shell ls ./*.in)
BASE_REQUIREMENTSTXT := $(patsubst %.in,%.txt,$(BASE_REQUIREMENTS))

.PHONY: all
all: compile-all-base

.PHONY: compile-test
compile-test:
	uv pip compile --python-version 3.10 --upgrade test.in -o test.txt --no-emit-package pip --no-emit-package setuptools

.PHONY: compile-dev
compile-dev:
	uv pip compile --python-version 3.10 --upgrade dev.in -o dev.txt --no-emit-package pip --no-emit-package setuptools

.PHONY: compile-base
compile-base:
	uv pip compile --python-version 3.10 --upgrade base.in -o base.txt --no-emit-package pip --no-emit-package setuptools

.PHONY: compile-all-base
compile-all-base: compile-base compile-test compile-dev
	@for file in $(BASE_REQUIREMENTS); do \
		echo -e "\n\ncompiling: $$file"; \
		uv pip compile --python-version 3.10 --upgrade --no-strip-extras $$file -o $${file%.in}.txt --no-emit-package pip --no-emit-package setuptools || exit 1; \
	done

.PHONY: clean
clean: clean-base

.PHONY: clean-base
clean-base:
	rm $(BASE_REQUIREMENTSTXT)
