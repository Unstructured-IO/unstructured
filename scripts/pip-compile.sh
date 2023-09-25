#!/usr/bin/env bash

# python version must match lowest supported (3.8)
major=3
minor=8
if ! python -c "import sys; assert sys.version_info.major == $major and sys.version_info.minor == $minor"; then
  echo "python version not equal to expected $major.$minor: $(python --version)"
  exit 1
fi

for file in requirements/*.in; do
  if [[ "$file" =~ "constraints" ]]; then
    continue;
  fi;
  echo "running: pip-compile --upgrade $file"
  pip-compile --upgrade "$file"
done
cp requirements/build.txt docs/requirements.txt
