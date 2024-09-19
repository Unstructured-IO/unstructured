#!/bin/bash

# NOTE(robinson) - this script installed mesa-gl 24.1. This is required because
# the mesa-gl 24.2 on the wolfi package manager does not included libgallium, which
# is required for the build to work. We can drop this work around as soon as mesa-gl
# is fixed upstream.

ARCH=$(uname -m)

if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
  files=(
    "mesa-gl-24.1-aarch64.0-r0.apk"
    "mesa-glapi-24.1.0-r0-aarch64.apk"
  )
else
  files=(
    "mesa-gl-24.1.0-r0.718c913d.apk"
    "mesa-glapi-24.1.0-r0.4390a503.apk"
  )
fi

for file in "${files[@]}"; do
  echo "Downloading ${file}"
  wget "https://utic-public-cf.s3.amazonaws.com/$file"
  apk add --allow-untrusted "${file}"
  rm "${file}"
done
