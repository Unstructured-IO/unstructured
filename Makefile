PACKAGE_NAME := unstructured
PIP_VERSION := 22.2.1


.PHONY: help
help: Makefile
	@sed -n 's/^\(***REMOVED******REMOVED*** \)\([a-zA-Z]\)/\2/p' $<


***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***
***REMOVED*** Install ***REMOVED***
***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***

***REMOVED******REMOVED*** install-base:            installs core requirements needed for text processing bricks
.PHONY: install-base
install-base: install-base-pip-packages install-nltk-models

***REMOVED******REMOVED*** install:                 installs all test, dev, and experimental requirements
.PHONY: install
install: install-base-pip-packages install-dev install-detectron2 install-nltk-models install-test

.PHONY: install-ci
install-ci: install-base-pip-packages install-pdf install-test install-nltk-models

.PHONY: install-base-pip-packages
install-base-pip-packages:
	python3 -m pip install pip==${PIP_VERSION}
	pip install -r requirements/base.txt

.PHONY: install-pdf
install-pdf:
	python3 -m pip install pip==${PIP_VERSION}
	pip install -r requirements/pdf.txt
	@echo "\n\n========================================================================"
	@echo " WARNING: PDF parsing capabilities in unstructured is still experimental"
	@echo "========================================================================\n\n"

.PHONY: install-detectron2
install-detectron2: install-pdf
	pip install "detectron2@git+https://github.com/facebookresearch/detectron2.git@v0.6***REMOVED***egg=detectron2"

.PHONE: install-nltk-models
install-nltk-models:
	python -c "import nltk; nltk.download('punkt')"
	python -c "import nltk; nltk.download('averaged_perceptron_tagger')"

.PHONY: install-test
install-test:
	pip install -r requirements/test.txt

.PHONY: install-dev
install-dev:
	pip install -r requirements/dev.txt

.PHONY: install-build
install-build:
	pip install -r requirements/build.txt

***REMOVED******REMOVED*** pip-compile:             compiles all base/dev/test requirements
.PHONY: pip-compile
pip-compile:
	pip-compile -o requirements/base.txt
	***REMOVED*** Extra requirements for parsing PDF files
	pip-compile --extra pdf -o requirements/pdf.txt
	***REMOVED*** NOTE(robinson) - We want the dependencies for detectron2 in the requirements.txt, but not
	***REMOVED*** the detectron2 repo itself. If detectron2 is in the requirements.txt file, an order of
	***REMOVED*** operations issue related to the torch library causes the install to fail
	sed 's/^detectron2 @/***REMOVED*** detectron2 @/g' requirements/pdf.txt
	pip-compile requirements/dev.in
	pip-compile requirements/test.in
	pip-compile requirements/build.in
	***REMOVED*** NOTE(robinson) - doc/requirements.txt is where the GitHub action for building
	***REMOVED*** sphinx docs looks for additional requirements
	cp requirements/build.txt docs/requirements.txt

***REMOVED******REMOVED*** install-project-local:   install unstructured into your local python environment
.PHONY: install-project-local
install-project-local: install
	***REMOVED*** MAYBE TODO: fail if already exists?
	pip install -e .

***REMOVED******REMOVED*** uninstall-project-local: uninstall unstructured from your local python environment
.PHONY: uninstall-project-local
uninstall-project-local:
	pip uninstall ${PACKAGE_NAME}

***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***
***REMOVED*** Test and Lint ***REMOVED***
***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED******REMOVED***

***REMOVED******REMOVED*** test:                    runs all unittests
.PHONY: test
test:
	PYTHONPATH=. pytest test_${PACKAGE_NAME} --cov=${PACKAGE_NAME} --cov-report term-missing

***REMOVED******REMOVED*** check:                   runs linters (includes tests)
.PHONY: check
check: check-src check-tests

***REMOVED******REMOVED*** check-src:               runs linters (source only, no tests)
.PHONY: check-src
check-src:
	black --line-length 100 ${PACKAGE_NAME} --check
	flake8 ${PACKAGE_NAME}
	mypy ${PACKAGE_NAME} --ignore-missing-imports

.PHONY: check-tests
check-tests:
	black --line-length 100 test_${PACKAGE_NAME} --check
	flake8 test_${PACKAGE_NAME}

***REMOVED******REMOVED*** tidy:                    run black
.PHONY: tidy
tidy:
	black --line-length 100 ${PACKAGE_NAME}
	black --line-length 100 test_${PACKAGE_NAME}

.PHONY: check-coverage
check-coverage:
	coverage report --fail-under=95
