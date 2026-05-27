# GitHub workflow guidance

This directory contains maintainer-facing repository automation and notes.

- Keep release-process documentation in `.github/README.md` or another maintainer-only repo doc, not in package `README.md` files that become PyPI project descriptions.
- Python package publish workflows should read package name/version from the package `pyproject.toml`, check PyPI for that exact version, and skip publishing if it already exists.
- Do not add automatic version bumping to publish workflows unless the release process is explicitly redesigned; package version bumps should be reviewed in PRs.
- Use the repository `PYPI_API_TOKEN` Actions secret for token-based PyPI publishing. Never commit token values or package credentials.
- Keep publish workflows scoped by `paths` to the package directory and the workflow file so unrelated merges do not trigger package release jobs.
