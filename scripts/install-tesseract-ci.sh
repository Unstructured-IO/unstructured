#!/usr/bin/env bash

# Used for installing tesseract on CI Ubuntu machine
# disable IPv6 in ci to avoid time out issue during add-apt-repository
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=1
sudo add-apt-repository -y ppa:alex-p/tesseract-ocr5
sudo apt-get install -y tesseract-ocr tesseract-ocr-kor
tesseract --version
installed_tesseract_version=$(tesseract --version | grep -oP '(?<=tesseract )\d+\.\d+\.\d+')

if [ "$installed_tesseract_version" != "${TESSERACT_VERSION}" ]; then
  echo "Tesseract version ${TESSERACT_VERSION} is required but found version $installed_tesseract_version"
  exit 1
fi
