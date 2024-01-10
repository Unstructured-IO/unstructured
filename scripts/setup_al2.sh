#!/usr/bin/env bash
set +u

if [ -z "$1" ]; then
  echo "When running this script, please supply the name of the user account for which to set up unstructured dependencies."
  echo "Ex: ${0} abertl"
  exit 1
fi

set -eux

# Set package manager command for this distribution
pac="yum"

# If we're not running as root, we want to prefix certain commands with sudo
if [[ $(whoami) == 'root' ]]; then
  $pac update -y
  $pac install -y sudo
  sudo=''
else
  type -p sudo >/dev/null || (echo "Please have an administrator install sudo and add you to the sudo group before continuing." && exit 1)
  sudo='sudo'
fi

# Set user account for which we're configuring the tools
USER_ACCOUNT=$1

# Update existing packages
$sudo $pac update -y

#### Utils
# Prerequisites
$sudo $pac install -y gcc wget tar curl make xz-devel
# Install non-ancient version of sed
wget http://ftp.gnu.org/gnu/sed/sed-4.9.tar.gz
tar xvf sed-4.9.tar.gz
cd sed-4.9/
./configure && make && $sudo make install
cd ..

#### Git
# Install git
$sudo $pac install -y git

#### Python
# Install tools needed to build python
$sudo $pac install -y bzip2 sqlite zlib-devel readline-devel sqlite-devel openssl-devel tk-devel libffi-devel bzip2-devel
# Install pyenv
sudo -u "$USER_ACCOUNT" -i <<'EOF'
    if [[ ! -d "$HOME"/.pyenv ]]; then
        cd $HOME
        curl https://pyenv.run | bash
        touch "$HOME"/.bashrc
        # Remove initialization lines from .bashrc if they are already there, so we don't duplicate them
        # shellcheck disable=SC2016
        sed -i '/export PYENV_ROOT="$HOME\/.pyenv"/d' "$HOME"/.bashrc
        # shellcheck disable=SC2016
        sed -i '/command -v pyenv >\/dev\/null || export PATH="$PYENV_ROOT\/bin:$PATH"/d' "$HOME"/.bashrc
        # shellcheck disable=SC2016
        sed -i '/eval "$(pyenv init -)"/d' "$HOME"/.bashrc
        # shellcheck disable=SC2016
        sed -i '/eval "$(pyenv virtualenv-init -)"/d' "$HOME"/.bashrc
        # Add initialization lines to .bashrc
        # shellcheck disable=SC2016
        cat <<'EOT' | cat - "$HOME"/.bashrc > temp && mv temp "$HOME"/.bashrc
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
EOT
        # install python
        source "$HOME"/.bashrc
        pyenv install 3.10.4
    fi
EOF

#### OpenCV dependencies
$sudo $pac install -y mesa-libGL

#### Poppler
# Install poppler
$sudo $pac install -y poppler-utils

#### Tesseract
# Install dependencies for image and pdf manipulation
$sudo $pac install -y opencv opencv-devel opencv-python perl-core clang libpng-devel libtiff-devel libwebp-devel libjpeg-turbo-devel git-core libtool pkgconfig xz
# Install leptonica (tesseract dependency)
wget https://github.com/DanBloomberg/leptonica/releases/download/1.75.1/leptonica-1.75.1.tar.gz
tar -xzvf leptonica-1.75.1.tar.gz
cd leptonica-1.75.1
./configure && make && $sudo make install
cd ..
# Install autoconf-archive (tesseract dependency)
wget http://mirror.squ.edu.om/gnu/autoconf-archive/autoconf-archive-2017.09.28.tar.xz
tar -xvf autoconf-archive-2017.09.28.tar.xz
cd autoconf-archive-2017.09.28
./configure && make && $sudo make install
$sudo cp m4/* /usr/share/aclocal
cd ..
# Install tesseract
git clone --depth 1 https://github.com/tesseract-ocr/tesseract.git tesseract-ocr
cd tesseract-ocr
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig
./autogen.sh
./configure && make && $sudo make install
cd ..
# Install tesseract languages
git clone https://github.com/tesseract-ocr/tessdata.git
$sudo cp tessdata/*.traineddata /usr/local/share/tessdata

#### libmagic
$sudo $pac install -y file-devel
