PIP = pip-compile --upgrade -o $@ $<
SHELL := /bin/bash
REQUIREMENTS := $(filter-out constraints.in base.in,$(shell find . -type f -name '*.in'))
# -not -name 'base.in' -not -name 'constraints.in' -not -name 'extra-pptx.txt')
REQUIREMENTSTXT := $(patsubst %.in,%.txt,$(REQUIREMENTS))

# those dependencies only needs constraint.in to and %.in to compile
constraint_dependent = base.txt extra-pptx.txt

.PHONY: all $(REQUIREMENTSTXT)

all: $(REQUIREMENTSTXT)

dev.txt: dev.in test.txt base.txt constraints.in
	$(PIP)

# the most common case: an extra (or test.txt) that depends on base.txt and %.in
$(REQUIREMENTSTXT): %.txt: %.in base.txt constraints.in
	$(PIP)

$(constraint_dependent): %.txt: %.in constraints.in
	$(PIP)
