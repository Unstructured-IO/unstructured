#!/usr/bin/env bash

# python version must match lowest supported (3.8)
major=3
minor=8
if ! python -c "import sys; assert sys.version_info.major == $major and sys.version_info.minor == $minor"; then
  echo "python version not equal to expected $major.$minor: $(python --version)"
  exit 1
fi

# NOTE(alan): Order matters in compiling. Start with base and test. Then do the rest in any order.
echo "running: pip-compile --upgrade base.in"
pip-compile --upgrade "requirements/base.in" -c requirements/constraints.in
echo "running: pip-compile --upgrade test.in"
pip-compile --upgrade "requirements/test.in" -c requirements/constraints.in

for file in requirements/*.in; do
  if [[ "$file" =~ "constraints" ]] || [[ "$file" =~ "base" ]] || [[ "$file" =~ "test" ]]; then
    continue;
  fi;
  echo "running: pip-compile --upgrade $file"
  pip-compile --upgrade "$file" -c requirements/constraints.in
done

for file in requirements/**/*.in; do
  if [[ "$file" =~ "constraints" ]] || [[ "$file" =~ "base" ]] || [[ "$file" =~ "test" ]]; then
    continue;
  fi;
  echo "running: pip-compile --upgrade $file"
  pip-compile --upgrade "$file" -c requirements/constraints.in
done
