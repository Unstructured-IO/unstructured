PIP = pip-compile --upgrade -o $@ $<

# those dependencies only needs constraint.in to and %.in to compile
constraint_dependent = base.txt extra-pptx.txt

# a special base that depend on two .txt files, constraints.in in addition to %.in
dev.txt: dev.in base.txt test.txt constraints.in
	$(PIP)

# the most common case: an extra (or test.txt) that depends on base.txt and %.in
$(filter-out constraints.txt base.txt, %.txt): %.in base.txt constraints.in
	echo "target: $@ prereq: $<"
	$(PIP)

$(constraint_dependent): %.txt: %.in constraints.in
	$(PIP)
