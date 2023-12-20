#!/usr/bin/env bash

# Mainly used for installing pandoc on CI
set -euo pipefail
if [ "${ARCH}" = "x86_64" ]; then
  export PANDOC_ARCH="amd64"
elif [ "${ARCH}" = "arm64" ] || [ "${ARCH}" = "aarch64" ]; then
  export PANDOC_ARCH="arm64"
fi

wget https://github.com/jgm/pandoc/releases/download/3.1.2/pandoc-3.1.2-linux-"${PANDOC_ARCH}".tar.gz
tar xvf pandoc-3.1.2-linux-"${PANDOC_ARCH}".tar.gz
cd pandoc-3.1.2
sudo cp bin/pandoc /usr/local/bin/
cd ..
rm -rf pandoc-3.1.2*
