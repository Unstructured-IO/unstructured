PIP = pip-compile --upgrade -o $@ $<
SHELL := /bin/bash
# we don't need to make constraints.txt from constraints.in
REQUIREMENTS := $(filter-out ./constraints.in,$(shell find . -type f -name '*.in'))
REQUIREMENTSTXT := $(patsubst %.in,%.txt,$(REQUIREMENTS))

# those dependencies only needs constraint.in to and %.in to compile
constraint_dependent = base.txt extra-pptx.txt

.PHONY: all $(REQUIREMENTSTXT)

all: $(REQUIREMENTSTXT)

# a special case where the .txt depends on other .txt; here dev.txt depends on test.txt
dev.txt: dev.in test.txt base.txt constraints.in
	$(PIP)

# the most common case: an extra (or test.txt) that depends on base.txt and %.in
$(REQUIREMENTSTXT): %.txt: %.in base.txt constraints.in
	$(PIP)

# special case where its only extra dependency is constraints.in; here base.txt and extra-ppt.txt
# only depends on their own .in and constraits.in
$(constraint_dependent): %.txt: %.in constraints.in
	$(PIP)

.PHONY: clean

clean:
	rm $(REQUIREMENTSTXT)
