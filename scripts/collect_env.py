import platform
import shutil
import subprocess

import pkg_resources

from unstructured.utils import dependency_exists


def command_exists(command):
    """
    Check if a command exists in the system

    Args:
        command (str): The command to check

    Returns:
        bool: True if command exists, False otherwise
    """
    return shutil.which(command) is not None


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


def is_python_package_installed(package_name: str):
    """
    Check if a Python package is installed

    Args:
        package_name (str): The Python package to check

    Returns:
        bool: True if package is installed, False otherwise
    """
    result = subprocess.run(
        ["pip", "list"],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )

    return any(line.lower().startswith(package_name.lower()) for line in result.stdout.splitlines())


def is_brew_package_installed(package_name: str):
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
        ["brew", "list"],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )

    for line in result.stdout.splitlines():
        if line.lower().startswith(package_name.lower()):
            return True

    result = subprocess.run(
        ["brew", "list", "--cask"],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )

    return any(line.lower().startswith(package_name.lower()) for line in result.stdout.splitlines())


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

    if dependency_exists("unstructured"):
        print("unstructured version: ", get_python_package_version("unstructured"))
    else:
        print("unstructured is not installed")

    if dependency_exists("unstructured_inference"):
        print(
            "unstructured-inference version: ",
            get_python_package_version("unstructured-inference"),
        )
    else:
        print("unstructured-inference is not installed")

    if dependency_exists("pytesseract"):
        print(
            "pytesseract version: ",
            get_python_package_version("pytesseract"),
        )
    else:
        print("pytesseract is not installed")

    if dependency_exists("torch"):
        print("Torch version: ", get_python_package_version("torch"))
    else:
        print("Torch is not installed")

    if dependency_exists("detectron2"):
        print("Detectron2 version: ", get_python_package_version("detectron2"))
    else:
        print("Detectron2 is not installed")

    if is_python_package_installed("paddlepaddle") or is_python_package_installed(
        "paddleocr",
    ):
        print(
            "PaddleOCR version: ",
            get_python_package_version("paddlepaddle") or get_python_package_version("paddleocr"),
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
