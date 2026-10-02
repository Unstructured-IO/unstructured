#!/usr/bin/env bash
set -euo pipefail

# Bound network operations separately so a slow mirror cannot hang CI, and a
# timeout never interrupts dpkg while it is changing the installed packages.
apt_options=(
  -o Acquire::http::Timeout=30
  -o Acquire::https::Timeout=30
  -o Acquire::Retries=2
  -o DPkg::Lock::Timeout=60
)

retry_download() {
  local attempt
  for attempt in 1 2 3; do
    echo "APT network attempt ${attempt}/3: $*"
    if sudo timeout --kill-after=30s 5m "$@"; then
      return 0
    fi
    if [[ "$attempt" != 3 ]]; then
      sleep 15
    fi
  done
  echo "APT network operation failed after three bounded attempts: $*" >&2
  return 1
}

install_packages() {
  retry_download apt-get "${apt_options[@]}" --download-only install -y "$@"
  sudo apt-get "${apt_options[@]}" --no-download install -y "$@"
}

retry_download apt-get "${apt_options[@]}" -o APT::Update::Error-Mode=any update
if [[ "${1:-}" == "--packages-only" ]]; then
  shift
  install_packages "$@"
  exit 0
fi
install_packages libmagic-dev poppler-utils libreoffice
# Avoid add-apt-repository's implicit, unbounded index download.
retry_download add-apt-repository --no-update -y ppa:alex-p/tesseract-ocr5
retry_download apt-get "${apt_options[@]}" -o APT::Update::Error-Mode=any update
install_packages tesseract-ocr tesseract-ocr-kor "$@"
tesseract --version
