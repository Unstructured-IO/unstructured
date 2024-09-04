SHELL := /bin/bash

BASE_REQUIREMENTS := $(shell ls ./*.in)
BASE_REQUIREMENTSTXT := $(patsubst %.in,%.txt,$(BASE_REQUIREMENTS))


.PHONY: all
all: compile-all-base

.PHONY: compile-test
compile-test:
	pip-compile --upgrade test.in

.PHONY: compile-dev
compile-dev:
	pip-compile --upgrade dev.in

.PHONY: compile-base
compile-base:
	pip-compile --upgrade base.in

.PHONY: compile-all-base
compile-all-base: compile-base compile-test compile-dev
	@$(foreach file,$(BASE_REQUIREMENTS),echo -e "\n\ncompiling: $(file)" && pip-compile --no-strip-extras --upgrade $(file) || exit;)

.PHONY: clean
clean: clean-base

.PHONY: clean-base
clean-base:
	rm $(BASE_REQUIREMENTSTXT)


