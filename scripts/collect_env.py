import subprocess
import platform
import pkg_resources


def command_exists(command):
    """
    Check if a command exists in the system

    Args:
        command (str): The command to check

    Returns:
        bool: True if command exists, False otherwise
    """
    try:
        subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False


def get_python_version():
    """
    Get the current Python version

    Returns:
        str: The current Python version
    """
    return platform.python_version()


def get_os_version():
    """
    Get the current operating system version

    Returns:
        str: The current operating system version
    """
    return platform.platform()


def is_python_package_installed(package_name):
    """
    Check if a Python package is installed

    Args:
        package_name (str): The Python package to check

    Returns:
        bool: True if package is installed, False otherwise
    """
    result = subprocess.run(
        ["pip", "list"], stdout=subprocess.PIPE, text=True, check=True
    )

    for line in result.stdout.splitlines():
        if line.lower().startswith(package_name.lower()):
            return True

    return False


def is_brew_package_installed(package_name):
    """
    Check if a Homebrew package is installed

    Args:
        package_name (str): The package to check

    Returns:
        bool: True if package is installed, False otherwise
    """
    if not command_exists("brew"):
        return False

    result = subprocess.run(
        ["brew", "list"], stdout=subprocess.PIPE, text=True, check=True
    )

    for line in result.stdout.splitlines():
        if line.lower().startswith(package_name.lower()):
            return True

    result = subprocess.run(
        ["brew", "list", "--cask"], stdout=subprocess.PIPE, text=True, check=True
    )

    for line in result.stdout.splitlines():
        if line.lower().startswith(package_name.lower()):
            return True

    return False


def get_python_package_version(package_name):
    """
    Get the version of a Python package

    Args:
        package_name (str): The Python package to check

    Returns:
        str: Version of the package, None if package is not installed
    """
    try:
        return pkg_resources.get_distribution(package_name).version
    except pkg_resources.DistributionNotFound:
        return None


def get_brew_package_version(package_name):
    """
    Get the version of a Homebrew package

    Args:
        package_name (str): The package to check

    Returns:
        str: Version of the package, None if package is not installed
    """
    if not command_exists("brew"):
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


def get_libmagic_version():
    """
    Get the version of libmagic

    Returns:
        str: Version of libmagic, None if libmagic is not installed
    """
    result = subprocess.run(
        ["file", "--version", "--headless"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return result.stdout.strip()


def get_libreoffice_version():
    """
    Get the version of LibreOffice

    Returns:
        str: Version of LibreOffice, None if LibreOffice is not installed
    """
    result = subprocess.run(
        ["libreoffice", "--version", "--headless"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return result.stdout.strip()


def main():
    """
    The main function to run all checks
    """
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

    if is_brew_package_installed("tesseract") or \
        is_python_package_installed("pytesseract"):
        print(
            "Tesseract version: ",
            get_brew_package_version("tesseract")
            or get_python_package_version("pytesseract"),
        )
    else:
        print("Tesseract is not installed")

    if is_python_package_installed("paddlepaddle") or \
        is_python_package_installed("paddleocr"):
        print(
            "PaddleOCR version: ",
            get_python_package_version("paddlepaddle")
            or get_python_package_version("paddleocr"),
        )
    else:
        print("PaddleOCR is not installed")

    if is_brew_package_installed("libmagic"):
        print("Libmagic version: ", get_brew_package_version("libmagic"))
    else:
        libmagic_version = get_libmagic_version()
        if libmagic_version:
            print(f"Libmagic version: {libmagic_version}")
        else:
            print("Libmagic is not installed")

    if platform.system() != "Windows":
        if is_brew_package_installed("libreoffice"):
            print("LibreOffice version: ", get_brew_package_version("libreoffice"))
        else:
            libreoffice_version = get_libreoffice_version()
            if libreoffice_version:
                print("LibreOffice version: ", libreoffice_version)
            else:
                print("LibreOffice is not installed")


if __name__ == "__main__":
    main()


# Output on Mac
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

# Output on Rocky Linux
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

# Output on Windows
# OS version:  Windows-10-10.0.20348-SP0
# Python version:  3.10.10
# unstructured version:  0.8.5
# unstructured-inference version:  0.5.7
# Detectron2 version:  0.5
# Torch version:  2.0.1
# Tesseract version:  0.3.10
# PaddleOCR version:  2.6.1.3
# Libmagic version: file-5.44
# magic file from /usr/share/misc/magic
