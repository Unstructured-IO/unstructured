#!/bin/bash

files=(
  "libreoffice-7.6.5-r0.apk"
  "openjpeg-2.5.0-r0.apk"
  "poppler-23.09.0-r0.apk"
  "leptonica-1.83.0-r0.apk"
  "pandoc-3.1.8-r0.apk"
  "tesseract-5.3.2-r0.apk"
  "nltk_data.tgz"

)

directory="docker-packages"
mkdir -p "${directory}"

for file in "${files[@]}"; do
  echo "Downloading ${file}"
  wget "https://utic-public-cf.s3.amazonaws.com/$file" -P "$directory"
done

echo "Downloads complete."
