## Summary

Explain the change and its user impact.

## Validation

Describe the relevant checks.

## Release note (optional)

Add user-facing detail beyond the PR title, especially migration steps for
breaking changes. The releaser copies this text into the GitHub Release.
Remove this section if the title is enough.

## Checklist

- [ ] The PR title is a user-facing release-note entry with a conventional commit prefix.
- [ ] Apply a category label (`enhancement`, `bug`, or an appropriate existing label), or ask a maintainer to apply it.
- [ ] For breaking changes, use `!` in the title and explain impact and migration above.

Ordinary PRs do not edit the frozen `CHANGELOG.md` or bump
`unstructured/__version__.py`. See the repository's CONTRIBUTING.md
for labels and the maintainer release workflow.
