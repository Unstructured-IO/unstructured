SHELL := /bin/bash

BASE_REQUIREMENTS := $(shell ls ./*.in)
BASE_REQUIREMENTSTXT := $(patsubst %.in,%.txt,$(BASE_REQUIREMENTS))

.PHONY: all
all: compile-all-base

.PHONY: compile-test
compile-test:
	uv pip compile --upgrade test.in -o test.txt

.PHONY: compile-dev
compile-dev:
	uv pip compile --upgrade dev.in -o dev.txt

.PHONY: compile-base
compile-base:
	uv pip compile --upgrade base.in -o base.txt

.PHONY: compile-all-base
compile-all-base: compile-base compile-test compile-dev
	@$(foreach file,$(BASE_REQUIREMENTS),echo -e "\n\ncompiling: $(file)" && uv pip compile --no-strip-extras --upgrade $(file) -o $${file%.in}.txt || exit;)

.PHONY: clean
clean: clean-base

.PHONY: clean-base
clean-base:
	rm $(BASE_REQUIREMENTSTXT)
