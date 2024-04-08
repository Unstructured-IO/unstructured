import collections
import os
import sys
import warnings
from typing import List

SUBSECTION_TYPES = ["### Enhancements", "### Features", "### Fixes"]


def ensure_changelog_folder_purity(folder_name):
    """Makes sure that the changelogs-dev folder only contains markdown files. This is to be able
    to raise an explicit error when an unexpected file is in the folder, rather than failing in
    an unexpected way later on."""
    for filename in os.listdir(folder_name):
        if not filename.endswith(".md"):
            raise ValueError(
                f"Found non-markdown changelog file named {filename} in the "
                f"changelog folder {folder_name}. Please ensure that changelogs "
                "are properly formatted."
            )


def parse_subsections(
    file_path, version_to_be_ensured=None, subsection_types=SUBSECTION_TYPES
) -> dict[str, List[str]]:
    """Parses the subsections of a changelog file, and returns them as a
    dictionary. This is to be able to combine data for each subsection separately, from different
    dev-changelog files. Check SUBSECTION_TYPES constant to see a list of valid subsections."""

    subsections = {}
    current_subsection_type = None

    with open(file_path) as file:
        for line in file:
            if any(subsection_type in line for subsection_type in subsection_types):
                current_subsection_type = line.strip()
                subsections[current_subsection_type] = []
            elif line and not line.isspace() and current_subsection_type:
                processed_line = line.strip().lstrip("-").lstrip(" ")
                subsections[current_subsection_type].append(processed_line)

    return subsections


def combine_files(folder_path, release_version) -> dict[str, List[str]]:
    """Combines the subsections of all changelog files in the folder.
    This is to be able to have individual changelog files which avoids conflicts in merge queues,
    and at the same time to save the burden from manually combining those files for each release"""
    ensure_changelog_folder_purity(folder_path)
    combined_subsections = {}

    # Iterate over files in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith(".md") and filename != "dev-changelog-template.md":
            file_path = os.path.join(folder_path, filename)
            file_subsections = parse_subsections(file_path, version_to_be_ensured=release_version)

            # Combine subsections from this file into the combined dictionary
            for subsection_type, lines in file_subsections.items():

                if subsection_type not in combined_subsections:
                    combined_subsections[subsection_type] = []
                combined_subsections[subsection_type].extend(lines)

        elif filename != "dev-changelog-template":
            warnings.warn(
                f"Found a non markdown file named {filename} in the changelogs-dev "
                "folder. File will be ignored."
            )

    return combined_subsections


def serialize_changelog_updates(combined_subsections, release_version):
    """Converts combined subsections dictionary into a markdown string, to be able to update the
    CHANGELOG.md file with the combined set of release notes."""
    changelog_updates = f"## {release_version}"
    for subsection_type, lines in combined_subsections.items():
        changelog_updates += f"\n\n{subsection_type}"
        for line in lines:
            changelog_updates += f"\n- {line}"
    changelog_updates += "\n\n"
    return changelog_updates


def increment_last_version(change_log_file):
    """Increments the last version number in the CHANGELOG.md file, after a previous release."""
    with open(change_log_file) as file:
        for line in file:
            if line.startswith("## "):
                last_version = line.strip().lstrip("## ")
                break
    last_version_parts = last_version.split(".")
    last_version_parts[-1] = str(int(last_version_parts[-1]) + 1)
    return ".".join(last_version_parts)


def get_changelog_updates(changelogs_dev_folder, release_version):
    """Combines the subsections of all changelog files in the folder, and returns them as a
    markdown string."""
    combined_subsections = collections.OrderedDict(
        sorted(combine_files(changelogs_dev_folder, release_version).items())
    )
    changelog_updates = serialize_changelog_updates(combined_subsections, release_version)
    return changelog_updates


def update_changelog_file(changelog_md_file_path, changelog_updates):
    """Updates the CHANGELOG.md file with the combined set of release notes."""
    with open(changelog_md_file_path) as file:
        existing_content = file.read()

    with open(changelog_md_file_path, "w") as file:
        file.write(changelog_updates + existing_content)


if __name__ == "__main__":
    if not len(sys.argv) >= 3:
        print(
            "Usage: python combine-changelogs.py <changelogs-dev folder path> "
            "<CHANGELOG.md file path> "
            "<release_version (optional)>"
        )
        sys.exit(1)

    changelogs_dev_folder, changelog_md_file_path, *optional_args = sys.argv[1:]
    release_version = (
        optional_args[0] if optional_args else increment_last_version(changelog_md_file_path)
    )

    changelog_updates = get_changelog_updates(changelogs_dev_folder, release_version)
    update_changelog_file(changelog_md_file_path, changelog_updates)
