***REMOVED***!/bin/bash
set +u

if [ -z "$1" ]; then
    echo "When running this script, please supply the name of the user account for which to set up unstructured dependencies."
    echo "Ex: ${0} abertl"
    exit 1
fi

set -eux

***REMOVED*** Set package manager command for this distribution
pac="apt"

***REMOVED*** If we're not running as root, we want to prefix certain commands with sudo
if [[ $(whoami) == 'root' ]]; then
    $pac update -y
    $pac install -y sudo
    sudo=''; else
    type -p sudo >/dev/null || (echo "Please have an administrator install sudo and add you to the sudo group before continuing." && exit 1)
    sudo='sudo'
fi

***REMOVED*** Set user account for which we're configuring the tools
USER_ACCOUNT=$1

***REMOVED*** Update existing packages
***REMOVED*** Reconfigure the service that detects the need for service restarts from interactive mode (user
***REMOVED*** needs to manually confirm which services to restart) to automatic. If we don't do this we'll
***REMOVED*** get hung up on a screen asking us which services we want to restart after upgrading packages.
$sudo $pac update -y
if [[ -d /etc/needrestart/conf.d ]]; then
    ***REMOVED*** shellcheck disable=SC2016
    echo '$nrconf{restart} = '"'a';" | $sudo tee /etc/needrestart/conf.d/99z_temp_disable.conf
fi
$sudo $pac upgrade -y

***REMOVED******REMOVED******REMOVED******REMOVED*** Utils
***REMOVED*** Prerequisites
$sudo env DEBIAN_FRONTEND="noninteractive" $pac install -y gcc wget tar curl make xz-utils build-essential tzdata

***REMOVED******REMOVED******REMOVED******REMOVED*** Git
***REMOVED*** Install git
$sudo $pac install -y git

***REMOVED******REMOVED******REMOVED******REMOVED*** Python
***REMOVED*** Install tools needed to build python
$sudo $pac install -y bzip2 sqlite zlib1g-dev libreadline-dev libsqlite3-dev libssl-dev tk-dev libffi-dev libbz2-dev llvm libncursesw5-dev libxml2-dev libxmlsec1-dev liblzma-dev
***REMOVED*** Install pyenv
sudo -u "$USER_ACCOUNT" -i <<'EOF'
    if [[ ! -d "$HOME"/.pyenv ]]; then
        cd $HOME
        curl https://pyenv.run | bash
        touch "$HOME"/.bashrc
        ***REMOVED*** Remove initialization lines from .bashrc if they are already there, so we don't duplicate them
        ***REMOVED*** shellcheck disable=SC2016
        sed -i '/export PYENV_ROOT="$HOME\/.pyenv"/d' "$HOME"/.bashrc
        ***REMOVED*** shellcheck disable=SC2016
        sed -i '/command -v pyenv >\/dev\/null || export PATH="$PYENV_ROOT\/bin:$PATH"/d' "$HOME"/.bashrc
        ***REMOVED*** shellcheck disable=SC2016
        sed -i '/eval "$(pyenv init -)"/d' "$HOME"/.bashrc
        ***REMOVED*** shellcheck disable=SC2016
        sed -i '/eval "$(pyenv virtualenv-init -)"/d' "$HOME"/.bashrc
        ***REMOVED*** Add initialization lines to .bashrc
        ***REMOVED*** shellcheck disable=SC2016
        cat <<'EOT' | cat - "$HOME"/.bashrc > temp && mv temp "$HOME"/.bashrc
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
EOT
        ***REMOVED*** install python
        source "$HOME"/.bashrc
        pyenv install 3.8.15
    fi
EOF

***REMOVED******REMOVED******REMOVED******REMOVED*** OpenCV dependencies
$sudo $pac install -y libgl1

***REMOVED******REMOVED******REMOVED******REMOVED*** Poppler
***REMOVED*** Install poppler
$sudo $pac install -y poppler-utils

***REMOVED******REMOVED******REMOVED******REMOVED*** Tesseract
***REMOVED*** Install tesseract as well as Russian language
$sudo $pac install -y tesseract-ocr libtesseract-dev tesseract-ocr-rus libreoffice pandoc

***REMOVED******REMOVED******REMOVED******REMOVED*** libmagic
$sudo $pac install -y libmagic-dev

***REMOVED******REMOVED******REMOVED******REMOVED*** Put needrestart back the way it was and clean up
if [[ -d /etc/needrestart/conf.d/ ]]; then
    $sudo rm -f /etc/needrestart/conf.d/99z_temp_disable.conf
fi
