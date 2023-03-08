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
install: install-base-pip-packages install-dev install-nltk-models install-test install-huggingface install-unstructured-inference

.PHONY: install-ci
install-ci: install-base-pip-packages install-nltk-models install-huggingface install-unstructured-inference install-test

.PHONY: install-base-pip-packages
install-base-pip-packages:
	python3 -m pip install pip==${PIP_VERSION}
	pip install -r requirements/base.txt

.PHONY: install-huggingface
install-huggingface:
	python3 -m pip install pip==${PIP_VERSION}
	pip install -r requirements/huggingface.txt

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

.PHONY: install-ingest-google-drive
install-ingest-google-drive:
	pip install -r requirements/ingest-google-drive.txt

***REMOVED******REMOVED*** install-ingest-s3:       install requirements for the s3 connector
.PHONY: install-ingest-s3
install-ingest-s3:
	pip install -r requirements/ingest-s3.txt

.PHONY: install-ingest-github
install-ingest-github:
	pip install -r requirements/ingest-github.txt

.PHONY: install-ingest-gitlab
install-ingest-gitlab:
	pip install -r requirements/ingest-gitlab.txt

.PHONY: install-ingest-reddit
install-ingest-reddit:
	pip install -r requirements/ingest-reddit.txt

.PHONY: install-ingest-wikipedia
install-ingest-wikipedia:
	pip install -r requirements/ingest-wikipedia.txt

.PHONY: install-unstructured-inference
install-unstructured-inference:
	pip install -r requirements/local-inference.txt

.PHONY: install-detectron2
install-detectron2:
	pip install "detectron2@git+https://github.com/facebookresearch/detectron2.git@v0.6***REMOVED***egg=detectron2"

***REMOVED******REMOVED*** install-local-inference: installs requirements for local inference
.PHONY: install-local-inference
install-local-inference: install install-unstructured-inference install-detectron2

***REMOVED******REMOVED*** pip-compile:             compiles all base/dev/test requirements
.PHONY: pip-compile
pip-compile:
	pip-compile --upgrade -o requirements/base.txt
	***REMOVED*** Extra requirements for huggingface staging functions
	pip-compile --upgrade --extra huggingface -o requirements/huggingface.txt
	***REMOVED*** NOTE(robinson) - We want the dependencies for detectron2 in the requirements.txt, but not
	***REMOVED*** the detectron2 repo itself. If detectron2 is in the requirements.txt file, an order of
	***REMOVED*** operations issue related to the torch library causes the install to fail
	pip-compile --upgrade requirements/dev.in
	pip-compile --upgrade requirements/test.in
	pip-compile --upgrade requirements/build.in
	pip-compile --upgrade --extra local-inference -o requirements/local-inference.txt
	***REMOVED*** NOTE(robinson) - doc/requirements.txt is where the GitHub action for building
	***REMOVED*** sphinx docs looks for additional requirements
	cp requirements/build.txt docs/requirements.txt
	pip-compile --upgrade --extra=s3        --output-file=requirements/ingest-s3.txt        requirements/base.txt setup.py
	pip-compile --upgrade --extra=reddit    --output-file=requirements/ingest-reddit.txt    requirements/base.txt setup.py
	pip-compile --upgrade --extra=github    --output-file=requirements/ingest-github.txt    requirements/base.txt setup.py
	pip-compile --upgrade --extra=gitlab    --output-file=requirements/ingest-gitlab.txt    requirements/base.txt setup.py
	pip-compile --upgrade --extra=wikipedia --output-file=requirements/ingest-wikipedia.txt requirements/base.txt setup.py
	pip-compile --upgrade --extra=google-drive --output-file=requirements/ingest-google-drive.txt  requirements/base.txt setup.py

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
check: check-src check-tests check-version

***REMOVED******REMOVED*** check-src:               runs linters (source only, no tests)
.PHONY: check-src
check-src:
	ruff . --select I,UP015,UP032,UP034,UP018,COM,C4,PT,SIM,PLR0402 --ignore PT011,PT012,SIM117
	black --line-length 100 ${PACKAGE_NAME} --check
	flake8 ${PACKAGE_NAME}
	mypy ${PACKAGE_NAME} --ignore-missing-imports --check-untyped-defs

.PHONY: check-tests
check-tests:
	black --line-length 100 test_${PACKAGE_NAME} --check
	flake8 test_${PACKAGE_NAME}

***REMOVED******REMOVED*** check-scripts:           run shellcheck
.PHONY: check-scripts
check-scripts:
    ***REMOVED*** Fail if any of these files have warnings
	scripts/shellcheck.sh

***REMOVED******REMOVED*** check-version:           run check to ensure version in CHANGELOG.md matches version in package
.PHONY: check-version
check-version:
    ***REMOVED*** Fail if syncing version would produce changes
	scripts/version-sync.sh -c -f "unstructured/__version__.py" semver

***REMOVED******REMOVED*** tidy:                    run black
.PHONY: tidy
tidy:
	ruff . --select I,UP015,UP032,UP034,UP018,COM,C4,PT,SIM,PLR0402 --fix-only || true
	black --line-length 100 ${PACKAGE_NAME}
	black --line-length 100 test_${PACKAGE_NAME}

***REMOVED******REMOVED*** version-sync:            update __version__.py with most recent version from CHANGELOG.md
.PHONY: version-sync
version-sync:
	scripts/version-sync.sh -f "unstructured/__version__.py" semver

.PHONY: check-coverage
check-coverage:
	coverage report --fail-under=95
