## Contributing to Unstructured

[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md)

👍🎉 First off, thank you for taking the time to contribute! 🎉👍

The following is a set of guidelines for contributing to the open source ecosystem of preprocessing pipeline APIs and supporting libraries hosted [here](https://github.com/Unstructured-IO).

This is meant to help the review process go smoothly, save the reviewer(s) time in catching common issues, and avoid submitting PRs that will be rejected by the CI.

In some cases it's convenient to put up a PR that's not ready for final review. This is fine (and under those circumstances it's not necessary to go through this checklist), but the PR should be put in draft mode so everyone knows it's not ready for review. 

### How to Contribute?

If you want to contribute, start working through the Unstructured codebase, navigate to the Github "issues" tab and start looking through interesting issues. If you are not sure of where to start, then start by trying one of the smaller/easier issues here i.e. issues with the "good first issue" label and then take a look at the issues with the "contributions welcome" label. These are issues that we believe are particularly well suited for outside contributions, often because we probably won't get to them right now. If you decide to start on an issue, leave a comment so that other people know that you're working on it. If you want to help out, but not alone, use the issue comment thread to coordinate.


## Pull-Request Checklist

The following is a list of tasks to be completed before submitting a pull request for final review.

### Before creating PR:

1. Follow coding best practices
    1. [ ] Make sure all new classes/functions/methods have docstrings.
    1. [ ] Make sure all new functions/methods have type hints (optional for tests).
    1. [ ] Make sure all new functions/methods have associated tests.
    1. [ ] Write a user-facing PR title and apply a category label (see below). Ordinary PRs do not edit `CHANGELOG.md` or bump `unstructured/__version__.py`.
<br/><br/>
1. Ensure environment is consistent
    1. [ ] Update dependencies in `.in` files if needed (pay special attention to whether the current PR depends on changes to internal repos that are not packaged - if so the commit needs to be bumped).
    1. [ ] If dependencies have changed, recompile dependencies with `make pip-compile`.
    1. [ ] Make sure local virtual environment matches what CI will see - reinstall internal/external dependencies as needed.\
<sub>Follow the [virtualenv install instructions](https://github.com/Unstructured-IO/community#mac--homebrew) if you are unsure about working with virtual environments.
<br/><br/>    
1. Run tests and checks locally
    1. [ ] Run tests locally with `make test`. Some repositories have supplemental tests with targets like `make test-integration` or `make test-sample-docs`. If applicable, run these as well. Try to make sure all tests are passing before submitting the PR, unless you are submitting in draft mode.
    1. [ ] Run typing, linting, and formatting checks with `make check`. Some repositories have supplemental checks with targets like `make check-scripts` or `make check-notebooks`. If applicable, run these as well. Try to make sure all checks are passing before submitting the PR, unless you are submitting in draft mode.
<br/><br/>    
1. Ensure code is clean
    1. [ ] Remove all debugging artifacts.
    1. [ ] Remove commented out code. 
    1. [ ] For actual comments, note that our typical format is `# NOTE(<username>): <comment>`
    1. [ ] Double check everything has been committed and pushed, recommended that local feature branch is clean.
    
### PR Guidelines:

1. [ ] PR title should follow [conventional commit](https://www.conventionalcommits.org/en/v1.0.0/) standards.
      
1. [ ] PR description should explain the change and its user impact. Add an optional "Release note" section when users need more detail than the title, especially for breaking changes.

1. [ ] If applicable, add a testing section to the PR description that recommends steps a reviewer can take to verify the changes, e.g. a snippet of code they can run locally.

### Release notes and versions

The PR title becomes the entry in GitHub generated release notes. Write it for
users and keep the conventional commit prefix. Apply `enhancement` for features,
`bug` for fixes, or an appropriate existing label such as `documentation` for
other changes. Maintainers can apply labels for external contributors.
Dependency PRs use `dependencies` and are excluded from generated notes; the
releaser must add user-relevant security updates during curation.

For breaking changes, add `!` to the title (for example `feat!: …`). Add a
"Release note" section that explains the impact and how to migrate. There is
no `breaking-change` label yet. Use an existing category label, and the
releaser will move the entry to Breaking changes. No new labels are required
to contribute.

`CHANGELOG.md` is frozen, including its existing release headings. Keep it
for historical links; do not add entries or synchronize it with the package.
The version format stays the same: several commits on `main` can share a
`-dev` or `-devN` version. Ordinary PRs, including dependency PRs, do not bump it.

### Release-day workflow (maintainers)

1. Prepare a release PR that changes `unstructured/__version__.py` from the
   current development version to its final version, for example `0.27.34-dev3` to
   `0.27.34`. Do not edit the frozen changelog.
2. Squash and merge the release PR so the final version is introduced in one
   commit. The `check-version` CI job rejects a final version that already has
   a version tag. It also blocks ordinary PRs while the base holds a final
   version, including merge-queue entries behind a release PR. These checks
   block merges only while `check-version` is a required status check on
   `main`.
3. Create the GitHub Release and tag from that release commit as today. Click
   **Generate release notes**, select the previous package release tag as the
   starting point, and curate the result. Check category labels, move breaking
   changes into their own section, paste useful "Release note" text from PRs,
   and add significant security or dependency changes excluded by the filter.
   For the first release under this convention, also carry forward relevant
   entries from the frozen changelog that are not in a published release so none
   are lost.
4. Publish the release using the existing process. Publication workflows are
   unchanged by this convention.
5. Publishing the release automatically opens a PR for the next patch `-dev`
   version. Another maintainer must approve it and enqueue it if auto-merge
   could not be enabled. The PR author is the owner of `GH_CREATE_PR_TOKEN`;
   that owner cannot approve their own PR. Ordinary PRs fail `check-version`
   until the bump lands. If the workflow fails (for example, the token expires),
   open and merge the bump PR by hand. The workflow depends on that existing
   secret; maintainers can retry it with `workflow_dispatch` and the release tag.

Ordinary PRs never need to think about the version. The guard checks the merge
result, so a stale PR that does not edit the version file passes after `main`
has moved to the next development version. Unchanged development versions pass
without checking tags. Release and bump PRs get tag checks: final versions must
not already be tagged, and development versions must not precede the latest
final release tag. Bare `-dev`, `-dev0`, and `.dev0` are equivalent; tags may
have a `v` or `unstructured_` prefix. Non-version tags and development tags do
not count as final releases.

The guard does not validate the commit a human selects when creating a GitHub
Release. Maintainers must still select the release commit and immediately merge
the next development bump. Automated tagging remains future work.

### License

Unstructured open source projects are licensed under the [Apache 2.0 license](https://www.apache.org/licenses/LICENSE-2.0).

Include a license at the top of new `setup.py` files:

- [Python license example](https://github.com/Unstructured-IO/unstructured/blob/main/setup.py)


## Conventions

For pull requests, our convention is to squash and merge. For PR titles, we use [conventional commit](https://www.freecodecamp.org/news/how-to-write-better-git-commit-messages/#conventional-commits) messages. The format should look like 

- `<type>: <description>`.

For example, if the PR addresses a new feature, the PR title should look like: 

- `feat: Implements exciting new feature`. 

For feature branches, the naming convention is:

- `<username>/<description>`. 

For the commit above, coming from the user called `contributor` the branch name would look like: 

- `contributor/exciting-new-feature`.

Here is a list of some of the most common possible commit types:

- `feat` – a new feature is introduced with the changes
- `fix` – a bug fix has occurred
- `chore` – changes that do not relate to a fix or feature and don't modify src or test files (for example updating dependencies)
- `refactor` – refactored code that neither fixes a bug nor adds a feature
- `docs` – updates to documentation such as a the README or other markdown files

### Why should you write better commit messages?

By writing good commits, you are simply future-proofing yourself. You could save yourself and/or coworkers hours of digging around while troubleshooting by providing that helpful description 🙂. 

The extra time it takes to write a thoughtful commit message as a letter to your potential future self is extremely worthwhile. On large scale projects, documentation is imperative for maintenance.

Collaboration and communication are of utmost importance within engineering teams. The Git commit message is a prime example of this. I highly suggest setting up a convention for commit messages on your team if you do not already have one in place.


## Code of Conduct

In the interest of fostering an open and welcoming environment, we as contributors and maintainers pledge to making participation in our project and our community a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Enforcement

Please report unacceptable behavior to support@unstructured.io. All complaints will be reviewed and investigated and will result in a response that is deemed necessary and appropriate to the circumstances. The project team is obligated to maintain confidentiality with regard to the reporter of an incident. Further details of specific enforcement policies may be posted separately.

Project maintainers who do not follow or enforce the Code of Conduct in good faith may face temporary or permanent repercussions as determined by other members of the project's leadership.

Thank you! 🤗

The Unstructured Team


## Learn more

| Section | Description |
|-|-|
| [Company Website](https://unstructured.io) | Unstructured.io product and company info |
| [Documentation](https://docs.unstructured.io/) | Full API documentation |
| [Working with Pull Requests](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests) | About pull requests |
| [Code of Conduct](https://www.contributor-covenant.org/version/1/4/code-of-conduct/) | Contributor Covenant Code Of Conduct |
| [Conventional Commits](https://www.freecodecamp.org/news/how-to-write-better-git-commit-messages/) | How to write better git commit messages |
| [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) | Lightweight convention on top of commit messages |
| [First Contributions](https://github.com/firstcontributions/first-contributions/blob/main/README.md) | Beginners' guide to make their first contribution! |


## Contributing Guides

If you're stumped 😓, here are some good examples of contribution guidelines:

- The GitHub Docs [contribution guidelines](https://github.com/github/docs/blob/main/CONTRIBUTING.md).
- The Ruby on Rails [contribution guidelines](https://github.com/rails/rails/blob/main/CONTRIBUTING.md).
- The Open Government [contribution guidelines](https://github.com/opengovernment/opengovernment/blob/master/CONTRIBUTING.md).
- The MMOCR [contribution guidelines](https://mmocr.readthedocs.io/en/dev-1.x/notes/contribution_guide.html).
- The HuggingFace [contribution guidelines](https://huggingface2.notion.site/Contribution-Guide-19411c29298644df8e9656af45a7686d).
