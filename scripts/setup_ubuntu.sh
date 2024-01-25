#!/usr/bin/env bash
set +u

if [ -z "$1" ]; then
  echo "When running this script, please supply the name of the user account for which to set up unstructured dependencies."
  echo "Ex: ${0} abertl"
  exit 1
fi

set -eux

# Set package manager command for this distribution
pac="apt"

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
# Reconfigure the service that detects the need for service restarts from interactive mode (user
# needs to manually confirm which services to restart) to automatic. If we don't do this we'll
# get hung up on a screen asking us which services we want to restart after upgrading packages.
$sudo $pac update -y
if [[ -d /etc/needrestart/conf.d ]]; then
  # shellcheck disable=SC2016
  echo '$nrconf{restart} = '"'a';" | $sudo tee /etc/needrestart/conf.d/99z_temp_disable.conf
fi
$sudo $pac upgrade -y

#### Utils
# Prerequisites
$sudo env DEBIAN_FRONTEND="noninteractive" $pac install -y gcc wget tar curl make xz-utils build-essential tzdata rsync

#### Git
# Install git
$sudo $pac install -y git

#### Python
# Install tools needed to build python
$sudo $pac install -y bzip2 sqlite zlib1g-dev libreadline-dev libsqlite3-dev libssl-dev tk-dev libffi-dev libbz2-dev llvm libncursesw5-dev libxml2-dev libxmlsec1-dev liblzma-dev
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
$sudo $pac install -y libgl1

#### Poppler
# Install poppler
$sudo $pac install -y poppler-utils

#### OpenOffice / MSOffice doc conversion capabilities
$sudo $pac install -y libreoffice pandoc

# Install tesseract 5 as well as Russian language
$sudo $pac install -y software-properties-common
$sudo add-apt-repository -y ppa:alex-p/tesseract-ocr5
$sudo $pac install -y tesseract-ocr libtesseract-dev tesseract-ocr-rus

#### libmagic
$sudo $pac install -y libmagic-dev

#### Put needrestart back the way it was and clean up
if [[ -d /etc/needrestart/conf.d/ ]]; then
  $sudo rm -f /etc/needrestart/conf.d/99z_temp_disable.conf
fi
