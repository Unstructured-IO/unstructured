#!/usr/bin/env bash

set -euo pipefail

# Shared script for Renovate to bump version and update CHANGELOG
# Can be downloaded and executed in any repo with version and changelog files
# Auto-detects changed dependencies from git diff

# Use current working directory as repo root (where Renovate executes the script)
# Override these via environment variables if your repo has different paths
REPO_ROOT="${REPO_ROOT:-$(pwd)}"
VERSION_FILE="${VERSION_FILE:-$REPO_ROOT/unstructured/__version__.py}"
CHANGELOG_FILE="${CHANGELOG_FILE:-$REPO_ROOT/CHANGELOG.md}"

echo "=== Renovate Security Version Bump ==="

# Read current version from __version__.py
CURRENT_VERSION=$(grep -o -E "(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-dev[0-9]+)?" "$VERSION_FILE")
echo "Current version: $CURRENT_VERSION"

# Determine release version based on current version format
if [[ "$CURRENT_VERSION" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)(-dev.*)?$ ]]; then
  MAJOR="${BASH_REMATCH[1]}"
  MINOR="${BASH_REMATCH[2]}"
  PATCH="${BASH_REMATCH[3]}"
  DEV_SUFFIX="${BASH_REMATCH[4]}"

  if [[ -n "$DEV_SUFFIX" ]]; then
    # Strip -dev suffix to release current version
    RELEASE_VERSION="$MAJOR.$MINOR.$PATCH"
    echo "Stripping dev suffix: $CURRENT_VERSION → $RELEASE_VERSION"
  else
    # Already a release version, bump to next patch
    NEW_PATCH=$((PATCH + 1))
    RELEASE_VERSION="$MAJOR.$MINOR.$NEW_PATCH"
    echo "Bumping patch version: $CURRENT_VERSION → $RELEASE_VERSION"
  fi
else
  echo "Error: Could not parse version: $CURRENT_VERSION"
  exit 1
fi

# Update __version__.py
echo "Updating $VERSION_FILE to version $RELEASE_VERSION"

# Detect quote style used in the file
if grep -q "__version__ = ['\"]" "$VERSION_FILE"; then
  if grep -q "__version__ = \"" "$VERSION_FILE"; then
    # Double quotes
    sed -i.bak -E "s/__version__ = \"[^\"]+\"/__version__ = \"$RELEASE_VERSION\"/" "$VERSION_FILE"
  else
    # Single quotes
    sed -i.bak -E "s/__version__ = '[^']+'/__version__ = '$RELEASE_VERSION'/" "$VERSION_FILE"
  fi
else
  echo "Error: Could not detect quote style in $VERSION_FILE"
  exit 1
fi

# Verify the update succeeded
if ! grep -q "__version__ = ['\"]${RELEASE_VERSION}['\"]" "$VERSION_FILE"; then
  echo "Error: Failed to update version in $VERSION_FILE"
  exit 1
fi

rm -f "$VERSION_FILE.bak"

# Detect changed packages from git diff (best effort, not critical)
echo "Detecting changed dependencies..."
CHANGED_PACKAGES=$(git diff --cached requirements/*.txt 2>/dev/null | grep -E "^[-+][a-zA-Z0-9_-]++=" | sed 's/^[+-]//' | sort -u | head -20 || true)

if [ -z "$CHANGED_PACKAGES" ]; then
  # Try without --cached
  CHANGED_PACKAGES=$(git diff requirements/*.txt 2>/dev/null | grep -E "^[-+][a-zA-Z0-9_-]++=" | sed 's/^[+-]//' | sort -u | head -20 || true)
fi

# Build changelog entry (generic for now, can be manually edited)
if [ -n "$CHANGED_PACKAGES" ]; then
  PACKAGE_COUNT=$(echo "$CHANGED_PACKAGES" | wc -l | tr -d ' ')
  echo "Found $PACKAGE_COUNT changed package(s)"
  CHANGELOG_ENTRY="- **Security update**: Bumped dependencies to address security vulnerabilities"
else
  echo "Could not auto-detect packages, using generic entry"
  CHANGELOG_ENTRY="- **Security update**: Bumped dependencies to address security vulnerabilities"
fi
echo "Changelog entry: $CHANGELOG_ENTRY"

# Update CHANGELOG.md
echo "Updating CHANGELOG..."

# Only look for -dev version to rename if CURRENT_VERSION had -dev suffix
if [[ -n "$DEV_SUFFIX" ]]; then
  # Look for -dev version header in CHANGELOG that matches our version
  DEV_VERSION_HEADER=$(grep -m 1 -F "## $CURRENT_VERSION" "$CHANGELOG_FILE" || true)

  if [[ -n "$DEV_VERSION_HEADER" ]]; then
    echo "Found dev version in CHANGELOG: $DEV_VERSION_HEADER"

    # Extract the -dev version number from header
    DEV_VERSION=$(echo "$DEV_VERSION_HEADER" | grep -o -E "[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]*")

    echo "Renaming CHANGELOG header: $DEV_VERSION → $RELEASE_VERSION"

    # Create awk script to:
    # 1. Rename the -dev version header
    # 2. Find or create Fixes section
    # 3. Append security entry
    awk -v dev_version="$DEV_VERSION" \
      -v release_version="$RELEASE_VERSION" \
      -v security_entry="$CHANGELOG_ENTRY" '
      BEGIN {
        in_target_version = 0
        found_fixes = 0
        added_entry = 0
      }

      # Match the dev version header and rename it
      /^## / {
        if ($0 ~ "^## " dev_version) {
          print "## " release_version
          in_target_version = 1
          next
        } else {
          # Hit a different version header, stop being in target version
          if (in_target_version && !found_fixes && !added_entry) {
            # We never found Fixes section, add it before this new version
            print ""
            print "### Fixes"
            print security_entry
            print ""
            added_entry = 1
          }
          in_target_version = 0
          found_fixes = 0
        }
      }

      # Found Fixes section in target version
      /^### Fixes/ && in_target_version {
        print
        print security_entry
        found_fixes = 1
        added_entry = 1
        next
      }

      { print }

      END {
        # Handle case where target dev version is last entry and has no Fixes section
        if (in_target_version && !found_fixes && !added_entry) {
          print ""
          print "### Fixes"
          print security_entry
        }
      }
    ' "$CHANGELOG_FILE" >"$CHANGELOG_FILE.tmp"

    mv "$CHANGELOG_FILE.tmp" "$CHANGELOG_FILE"
  else
    # Dev version in __version__.py but no dev header found in CHANGELOG
    # This shouldn't happen, but create new entry as fallback
    echo "Warning: Current version has -dev suffix but no matching dev header in CHANGELOG"
    echo "Creating new entry for $RELEASE_VERSION"

    cat >/tmp/new_changelog_section.tmp <<EOF
## $RELEASE_VERSION

### Fixes
$CHANGELOG_ENTRY

EOF

    cat /tmp/new_changelog_section.tmp "$CHANGELOG_FILE" >"$CHANGELOG_FILE.tmp"
    mv "$CHANGELOG_FILE.tmp" "$CHANGELOG_FILE"
    rm -f /tmp/new_changelog_section.tmp
  fi
else
  # Current version was already a release, so we bumped to next patch
  # Create new release entry at top
  echo "Current version was already released, creating new entry for $RELEASE_VERSION"

  cat >/tmp/new_changelog_section.tmp <<EOF
## $RELEASE_VERSION

### Fixes
$CHANGELOG_ENTRY

EOF

  cat /tmp/new_changelog_section.tmp "$CHANGELOG_FILE" >"$CHANGELOG_FILE.tmp"
  mv "$CHANGELOG_FILE.tmp" "$CHANGELOG_FILE"
  rm -f /tmp/new_changelog_section.tmp
fi

echo ""
echo "✓ Successfully updated version to $RELEASE_VERSION"
echo "✓ Updated CHANGELOG with security fix entry"
echo ""
echo "Modified files:"
echo "  - $VERSION_FILE"
echo "  - $CHANGELOG_FILE"
