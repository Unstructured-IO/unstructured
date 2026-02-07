#!/usr/bin/env bash

set -euo pipefail

# Allowed license families (partial-match against the License metadata field).
# Covers the standard permissive + weak-copyleft licenses the project accepts.
# Build the semicolon-separated allowlist for --partial-match.
# Each entry is matched as a case-insensitive substring against the package's
# License metadata field. Order does not matter.
ALLOWED="Apache;\
BSD;\
MIT;\
ISC;\
MPL;\
Mozilla;\
LGPL;\
GNU Lesser General Public License;\
GNU Library or Lesser General Public License;\
GNU General Public License v2;\
PSF;\
Python Software Foundation;\
Unlicense;\
HPND;\
Historical Permission Notice and Disclaimer;\
CNRI-Python;\
Python-2.0"

# Packages whose license metadata is missing, non-standard, or proprietary but
# known-good for this project. Each has been manually verified against the
# upstream source repository.
IGNORED_PACKAGES=(
  # Metadata missing -- verified permissive on GitHub
  arro3-core     # MIT / Apache-2.0 (geoarrow/geoarrow-rs)
  chroma-hnswlib # Apache-2.0 (chroma-core/hnswlib)
  google-crc32c  # Apache-2.0 (googleapis/python-crc32c)
  iopath         # MIT (facebookresearch/iopath)
  pypdfium2      # BSD-3-Clause (PDFium/PDFium)
  voyageai       # MIT (voyage-ai/voyageai-python)

  # Permissive but non-standard classifier
  lmdb # OpenLDAP Public License (BSD-style, jnwatson/py-lmdb)
  pykx # KDB+ proprietary (KxSystems/pykx, transitive dep of kdbai-client)

  # NVIDIA CUDA runtime libs (proprietary, torch transitive dependencies)
  cuda-bindings
  nvidia-cublas-cu12
  nvidia-cuda-cupti-cu12
  nvidia-cuda-nvrtc-cu12
  nvidia-cuda-runtime-cu12
  nvidia-cudnn-cu12
  nvidia-cufft-cu12
  nvidia-cufile-cu12
  nvidia-curand-cu12
  nvidia-cusolver-cu12
  nvidia-cusparse-cu12
  nvidia-cusparselt-cu12
  nvidia-nccl-cu12
  nvidia-nvjitlink-cu12
  nvidia-nvshmem-cu12
  nvidia-nvtx-cu12
)

echo "Checking licenses for installed packages..."
uv run pip-licenses \
  --partial-match \
  --allow-only="$ALLOWED" \
  --ignore-packages "${IGNORED_PACKAGES[@]}"
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "All dependencies have authorized licenses."
else
  echo "There are dependencies with unauthorized or unknown licenses."
  exit 1
fi
