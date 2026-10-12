# Lives here, not in the root Makefile, which the org template sync rewrites.
.PHONY: skills skills-check
skills:
	node skills/build.mjs

# Fails when generated skills differ from what `make skills` produces, including hand edits and stray files.
skills-check: skills
	@test -z "$$(git status --porcelain grok/skills pi/skills cli/skills)" || { git status --porcelain grok/skills pi/skills cli/skills; echo "Generated skills are stale or hand-edited: edit skills/, run make skills, commit."; exit 1; }
