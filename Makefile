SHELL := /usr/bin/env bash

include $(wildcard makefiles/*)

.PHONY: check-trufflehog
check-trufflehog:
	@if ! which trufflehog > /dev/null 2>&1; then \
		echo "TruffleHog is not installed."; \
		echo "MacOS users can install it with:"; \
		echo "  brew install trufflehog"; \
		echo ""; \
		echo "Linux users can install it with:"; \
		echo "  curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin"; \
		echo ""; \
		echo "For more details, go to https://github.com/trufflesecurity/trufflehog"; \
		exit 1; \
	fi

.PHONY: setup-pre-commit
setup-pre-commit:
	@if [ ! -f .pre-commit-config.yaml ]; then \
		echo ".pre-commit-config.yaml not found. Copying template..."; \
		cp .github/config/.pre-commit-config-template.yaml .pre-commit-config.yaml; \
		echo ".pre-commit-config.yaml created from template."; \
	else \
		echo ".pre-commit-config.yaml already exists."; \
	fi

.PHONY: init
init: setup-pre-commit check-trufflehog
	pip install pre-commit
	pre-commit install

.PHONY: skills skills-check
skills:
	node skills/build.mjs

# Fails when generated skills differ from what `make skills` produces, including hand edits and stray files.
skills-check: skills
	@test -z "$$(git status --porcelain grok/skills pi/skills)" || { git status --porcelain grok/skills pi/skills; echo "Generated skills are stale or hand-edited: edit skills/, run make skills, commit."; exit 1; }
