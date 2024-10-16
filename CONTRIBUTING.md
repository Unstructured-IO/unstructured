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
    1. [ ] Update `CHANGELOG.md` and `__version__.py` if the core code has changed
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
      
1. [ ] PR description should give enough detail that the reviewer knows what they reviewing - sometimes a copy-paste of the added `CHANGELOG.md` items is enough, sometimes more detail is needed.

1. [ ] If applicable, add a testing section to the PR description that recommends steps a reviewer can take to verify the changes, e.g. a snippet of code they can run locally.

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
| [Documentation](https://unstructured-io.github.io/unstructured) | Full API documentation |
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
