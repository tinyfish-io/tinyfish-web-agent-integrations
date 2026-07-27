# Writing the synthesis

For prose answers rather than structured rows. Assumes searching and fetching are done and you're
turning findings into something worth reading.

## Organize by finding, not by source

The wrong shape is a tour of what each source said. The right shape is a claim per section, with the
sources as evidence underneath it. If two sources support one point, that's one section with two
citations — not two sections.

Group by theme, order by what matters most to the question asked, and lead each section with its
conclusion rather than building to it.

## Cite specifically

- Link inline, on the words that carry the claim — not a bare URL, and not a numbered footnote pile at
  the end.
- **Cite what you actually read.** A snippet is not a source. If you didn't fetch the page, don't
  attribute a quote or a number to it.
- Attribute contested claims to who made them: "Vercel's team reports X" rather than a flat "X".
- Give dates for anything time-sensitive, and use `published_date` from the fetch result rather than a
  date in the body text.

## Distinguish what you know from what you inferred

The three are different and readers can't tell them apart unless you do:

- **Established** — multiple independent sources, or a primary source.
- **Claimed** — one source, or a source with an interest in the answer.
- **Inferred** — your reasoning from the above. Say so.

One source agreeing with itself across three blog posts is one source. A vendor benchmarking itself
against competitors is a claim, not a finding.

## Report the gaps

The honest limits of the research are part of the answer:

- What you looked for and couldn't find. Absence of evidence is often the most useful line in the
  report — it tells the user where not to look next.
- Where sources disagreed. Don't average conflicting numbers into a fake consensus; state the range
  and who's on each side.
- What you excluded and why — SEO listicles, undated posts, marketing pages with no methodology.

## Length

Fit the answer to the question, not to the volume of material gathered. Reviewing 200 sources does not
license 2000 words. Target about one screen; if the material genuinely needs more, write the full
version to `./tinyfish-results/<topic>-<YYYY-MM-DD>.md` and keep the one-screen version as the answer.

## Style

- No emojis unless the user asked for them.
- Tables when fields are uniform; prose when they aren't. Don't force heterogeneous findings into a
  grid — a table with half its cells reading "N/A" is worse than three sentences.
- Cut hedging that carries no information. "It appears that X may possibly be the case" is "X,
  according to one source."
- Define a term the first time it appears if it's specific to the domain, then use it consistently.
- No preamble. Start with the answer.
