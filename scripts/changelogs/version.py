import sys


def get_last_version(version_file):
    """Reads the last version from the version file."""
    with open(version_file) as file:
        last_version = file.read().split('"')[1]
    return last_version


def last_version_is_dev(last_version):
    """Used to determine if the last version is a development version."""
    return "dev" in last_version


def increment_last_release_version(last_version):
    """Used to determine the next version when the last version is a release version."""
    last_version_parts = last_version.split(".")
    last_version_parts[-1] = str(int(last_version_parts[-1]) + 1)
    return ".".join(last_version_parts)


def update_version_file(version_file, version):
    """Updates the version file with the new version."""
    with open(version_file, "w") as file:
        file.write(f'__version__ = "{version}"  # pragma: no cover\n')


def get_next_version(next_version_type, last_version):
    if next_version_type == "dev":
        if last_version_is_dev(last_version):
            # Version file remains the same with a -dev suffix
            sys.exit(0)
        else:
            # We increment the last release version and add a -dev suffix
            next_version = increment_last_release_version(last_version) + "-dev"
            return next_version

    elif next_version_type == "release":
        if last_version_is_dev(last_version):
            # We remove the -dev suffix
            next_version = last_version.split("-")[0]
            return next_version

        else:
            # Two release versions in a row is an edge case, where we cannot be sure what the
            # expected behavior is. In this case, we ask for manual intervention.
            print(
                "You are trying to make a release version when the last version is also a release"
                "version. Please handle all file modifications manually."
            )
            sys.exit(1)

    else:
        print("Usage: python version.py <next_version_type (dev or release)> ")
        sys.exit(1)


if __name__ == "__main__":
    """This script gets the next version type (dev or release) from the user, and makes
    the necessary changes to the version file (if any changes are needed)."""

    if len(sys.argv) == 1:
        print("Usage: python version.py <next version type (dev or release)> ")
        sys.exit(1)

    OUTPUT_FILE = "unstructured/__version__.py"

    # Used to determine if the next version will have a -dev suffix or not,
    # and, to determine if we need to increment the version
    next_version_type = sys.argv[1]

    last_version = get_last_version(OUTPUT_FILE)
    next_version = get_next_version(next_version_type, last_version)
    update_version_file(OUTPUT_FILE, next_version)
