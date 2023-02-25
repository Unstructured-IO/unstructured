#!/bin/bash
set +u -e

if [ -z "$1" ]; then
    echo "When running this script, please supply the name of the user account for which to set up unstructured dependencies."
    echo "Ex: ${0} abertl"
    exit 1
fi

set -ux

# Set user account for which we're configuring the tools
USER_ACCOUNT=$1

# Set package manager command for this distribution
pac="apt"

# If we're not running as root, we want to prefix certain commands with sudo
if [[ $(whoami) == 'root' ]]; then
    sudo=''; else
    sudo='sudo'
fi

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

#### Git
# Install git
$sudo $pac install -y git

#### Python
# Install tools needed to build python
$sudo $pac install -y curl gcc bzip2 sqlite zlib1g-dev libreadline-dev libsqlite3-dev libssl-dev tk-dev libffi-dev xz-utils make build-essential libbz2-dev wget llvm libncursesw5-dev libxml2-dev libxmlsec1-dev liblzma-dev
# Install pyenv
if [[ ! -d /home/$USER_ACCOUNT/.pyenv ]]; then
    sudo -u "$USER_ACCOUNT" -i <<'EOF'
    cd $HOME
    curl https://pyenv.run | bash
EOF
    # Remove initialization lines from .bashrc if they are already there, so we don't duplicate them
    # shellcheck disable=SC2016
    sed -i '/export PYENV_ROOT="$HOME\/.pyenv"/d' /home/"$USER_ACCOUNT"/.bashrc
    # shellcheck disable=SC2016
    sed -i '/command -v pyenv >\/dev\/null || export PATH="$PYENV_ROOT\/bin:$PATH"/d' /home/"$USER_ACCOUNT"/.bashrc
    # shellcheck disable=SC2016
    sed -i '/eval "$(pyenv init -)"/d' /home/"$USER_ACCOUNT"/.bashrc
    # shellcheck disable=SC2016
    sed -i '/eval "$(pyenv virtualenv-init -)"/d' /home/"$USER_ACCOUNT"/.bashrc
    # Add initialization lines to .bashrc
    # shellcheck disable=SC2016
    sed -i '1ieval "$(pyenv virtualenv-init -)"' /home/"$USER_ACCOUNT"/.bashrc
    # shellcheck disable=SC2016
    sed -i '1ieval "$(pyenv init -)"' /home/"$USER_ACCOUNT"/.bashrc
    # shellcheck disable=SC2016
    sed -i '1icommand -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' /home/"$USER_ACCOUNT"/.bashrc
    # shellcheck disable=SC2016
    sed -i '1iexport PYENV_ROOT="$HOME/.pyenv"' /home/"$USER_ACCOUNT"/.bashrc
    # install python
    sudo -u "$USER_ACCOUNT" -i <<'EOF'
    pyenv install 3.8.15
EOF
fi

#### OpenCV dependencies
$sudo $pac install -y libgl1

#### Poppler
# Install poppler
$sudo $pac install -y poppler-utils

#### Tesseract
# Install tesseract as well as Russian language
$sudo $pac install -y tesseract-ocr libtesseract-dev tesseract-ocr-rus

#### libmagic
$sudo $pac install libmagic-dev

#### Put needrestart back the way it was and clean up
if [[ -d /etc/needrestart/conf.d/ ]]; then
    $sudo rm -f /etc/needrestart/conf.d/99z_temp_disable.conf
fi
