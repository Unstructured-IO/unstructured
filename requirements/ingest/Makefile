VPATH = ..
PIP = pip-compile --upgrade -o $@ $<

%.txt: %.in base.txt constraints.in
	echo "target: $@ prereq: $<"
	$(PIP)
