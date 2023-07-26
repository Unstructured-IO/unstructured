import subprocess
import platform
import pkg_resources


def command_exists(command):
    # Check if a command exists in the system
    try:
        subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False


def get_python_version():
    return platform.python_version()


def get_os_version():
    return platform.platform()


def is_python_package_installed(package_name):
    result = subprocess.run(
        ["pip", "list"], stdout=subprocess.PIPE, text=True, check=True
    )
    for line in result.stdout.splitlines():
        if line.lower().startswith(package_name.lower()):
            return True
    return False


def is_brew_package_installed(package_name):
    # Check if a Homebrew package is installed by scanning the output of `brew list` and `brew list --cask`
    if not command_exists('brew'):
        return False
    result = subprocess.run(['brew', 'list'], stdout=subprocess.PIPE, text=True, check=True)
    for line in result.stdout.splitlines():
        if line.lower().startswith(package_name.lower()):
            return True
    result = subprocess.run(['brew', 'list', '--cask'], stdout=subprocess.PIPE, text=True, check=True)
    for line in result.stdout.splitlines():
        if line.lower().startswith(package_name.lower()):
            return True
    return False


def is_apt_package_installed(package_name):
    # Check if 'dpkg' command exists in the system
    if not command_exists('dpkg'):
        return False
    result = subprocess.run(
        ["dpkg", "--get-selections"], stdout=subprocess.PIPE, text=True, check=True
    )
    for line in result.stdout.splitlines():
        if line.lower().startswith(package_name.lower() + "\t"):
            return True
    return False


def get_python_package_version(package_name):
    try:
        return pkg_resources.get_distribution(package_name).version
    except pkg_resources.DistributionNotFound:
        return None


def is_dnf_or_yum_package_installed(package_name):
    if command_exists("dnf"):
        result = subprocess.run(["dnf", "list", "installed", package_name], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    elif command_exists("yum"):
        result = subprocess.run(["yum", "list", "installed", package_name], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    else:
        return False

    return package_name in result.stdout


def get_brew_package_version(package_name):
    if not command_exists('brew'):
        return None
    
    result = subprocess.run(
        ["brew", "info", package_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    for line in result.stdout.splitlines():
        return line
    return None


def get_apt_package_version(package_name):
    if not command_exists('apt'):
        return None
    
    result = subprocess.run(
        ["apt", "show", package_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("Version:"):
            return line.split("Version:")[1].strip()
    return None


def get_dnf_or_yum_package_version(package_name):
    if command_exists("dnf"):
        result = subprocess.run(["dnf", "list", package_name], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    elif command_exists("yum"):
        result = subprocess.run(["yum", "list", package_name], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    else:
        return None

    for line in result.stdout.splitlines():
        if package_name in line:
            return line.split()[1]  # The version is the second column
    return None


def get_libmagic_version():
    result = subprocess.run(['file', '--version', '--headless'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip()


def get_libreoffice_version():
    result = subprocess.run(['libreoffice', '--version', '--headless'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip()


def main():
    print("OS version: ", get_os_version())
    print("Python version: ", get_python_version())

    if is_python_package_installed("unstructured"):
        print("unstructured version: ", get_python_package_version("unstructured"))
    else:
        print("unstructured is not installed")

    if is_python_package_installed("unstructured-inference"):
        print(
            "unstructured-inference version: ",
            get_python_package_version("unstructured-inference"),
        )
    else:
        print("unstructured-inference is not installed")

    if is_python_package_installed("detectron2"):
        print("Detectron2 version: ", get_python_package_version("detectron2"))
    else:
        print("Detectron2 is not installed")

    if is_python_package_installed("torch"):
        print("Torch version: ", get_python_package_version("torch"))
    else:
        print("Torch is not installed")

    if is_brew_package_installed("tesseract") or is_apt_package_installed("tesseract") or is_python_package_installed("pytesseract"):
        print("Tesseract version: ", get_brew_package_version("tesseract") or get_apt_package_version("tesseract") or get_python_package_version("pytesseract"))
    else:
        print("Tesseract is not installed")

    if is_python_package_installed("paddlepaddle") or is_python_package_installed("paddleocr"):
        print("PaddleOCR version: ", get_python_package_version("paddlepaddle") or get_python_package_version("paddleocr"))
    else:
        print("PaddleOCR is not installed")

    if is_brew_package_installed("libmagic") or is_apt_package_installed("libmagic1") or is_dnf_or_yum_package_installed("libmagic"):
        print("Libmagic version: ", get_brew_package_version("libmagic") or get_apt_package_version("libmagic1") or get_dnf_or_yum_package_version("libmagic"))
    else:
        libmagic_version = get_libmagic_version()
        if libmagic_version:
            print(f"Libmagic version: {libmagic_version}")
        else:
            print("Libmagic is not installed")

    # if is_brew_package_installed("libreoffice") or is_apt_package_installed("libreoffice") or is_dnf_or_yum_package_installed("libreoffice"):
    #     print("LibreOffice version: ", get_brew_package_version("libreoffice") or get_apt_package_version("libreoffice") or get_dnf_or_yum_package_version("libreoffice") or get_libreoffice_version())
    # else:
    #     libreoffice_version = get_libreoffice_version()
    #     if libreoffice_version:
    #         print("LibreOffice version: ", libreoffice_version)
    #     else:
    #         print("LibreOffice is not installed")

    if is_brew_package_installed("libreoffice") or is_apt_package_installed("libreoffice") or is_dnf_or_yum_package_installed("libreoffice"):
        print("LibreOffice version: ", get_brew_package_version("libreoffice") or get_apt_package_version("libreoffice") or get_dnf_or_yum_package_version("libreoffice"))
    else:
        libreoffice_version = get_libreoffice_version()
        if libreoffice_version:
            print("LibreOffice version: ", libreoffice_version)
        else:
            print("LibreOffice is not installed")



    # if is_brew_package_installed("libmagic"):
    #     print("Libmagic version: ", get_brew_package_version("libmagic"))
    # elif is_apt_package_installed("libmagic1"):
    #     print("Libmagic version: ", get_apt_package_version("libmagic1"))
    # else:
    #     print("Libmagic is not installed")

    # if is_brew_package_installed("libreoffice"):
    #     print("LibreOffice version: ", get_brew_package_version("libreoffice"))
    # elif is_apt_package_installed("libreoffice"):
    #     print("LibreOffice version: ", get_apt_package_version("libreoffice"))
    # else:
    #     print("LibreOffice is not installed")


if __name__ == "__main__":
    main()


# on Mac
# OS version:  macOS-13.4.1-arm64-arm-64bit
# Python version:  3.8.17
# unstructured version:  0.5.11
# unstructured-inference version:  0.3.2
# Detectron2 version:  0.6
# Torch version:  2.0.0
# Tesseract version:  ==> tesseract: stable 5.3.1 (bottled), HEAD
# PaddleOCR version:  2.5.0
# Libmagic version:  ==> libmagic: stable 5.44 (bottled)
# LibreOffice version:  ==> libreoffice: 7.5.4

# On Linux
# OS version:  Linux-5.15.49-linuxkit-pr-aarch64-with-glibc2.28
# Python version:  3.8.17
# unstructured version:  0.8.1
# unstructured-inference version:  0.5.5
# Detectron2 is not installed
# Torch version:  2.0.1
# Tesseract version:  0.3.10
# PaddleOCR version:  2.6.1.3
# Libmagic version: file-5.33
# magic file from /etc/magic:/usr/share/misc/magic
# LibreOffice version:  LibreOffice 6.4.7.2 40(Build:2)
