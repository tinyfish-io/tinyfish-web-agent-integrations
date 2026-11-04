# Lives here, not in the root Makefile, which the org template sync rewrites.
.PHONY: skills skills-check
SKILL_DIRS = $(shell node -e "import('./skills/build.mjs').then((m) => console.log(Object.values(m.TARGETS).join(' ')))")
skills:
	node skills/build.mjs

# Fails when generated skills differ from what `make skills` produces, including hand edits and stray files.
skills-check: skills
	@test -z "$$(git status --porcelain $(SKILL_DIRS))" || { git status --porcelain $(SKILL_DIRS); echo "Generated skills are stale or hand-edited: edit skills/, run make skills, commit."; exit 1; }
