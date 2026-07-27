# Decomposing a question into parallel work

Read this before splitting a question across subagents. The orchestrator uses it; subagents don't
need it.

## The unit of decomposition is a sub-question, not a keyword

Give each subagent a question it can answer on its own. "Search for competitor pricing" is a chore;
"Which competitors publish per-seat pricing, and what do they charge at the 50-seat tier?" is a
question with a checkable answer.

## Split by angle, never by synonym

The failure mode is dispatching four subagents that all return the same pages. Synonym rewrites hit
the same semantic region and waste the pass.

Angles that actually diverge:

| Angle | Finds |
|---|---|
| **Advocates** | What people who chose it say about using it in production |
| **Defectors** | Why teams migrated away; failure modes; complaints |
| **Recent** | What launched or shifted in the last N months and isn't widely known yet |
| **Adjacent** | What the alternatives are, including ones the user didn't name |
| **Primary sources** | Docs, filings, specs, changelogs — not commentary |
| **Quantitative** | Benchmarks, pricing, headcount, citation counts |

Worked example — "best open-source LLM fine-tuning frameworks for production":

1. What do engineers running fine-tuning in production say about the frameworks they chose, and why?
2. Which frameworks launched or gained traction in the last 6 months that aren't yet widely discussed?
3. What are the common failure modes and reasons teams abandoned specific frameworks in production?
4. What do published benchmarks and cost comparisons show across the main contenders?

Four subagents, four disjoint result sets, one coherent picture. Contrast with "best fine-tuning
frameworks" / "top fine-tuning libraries" / "fine-tuning framework comparison" — three subagents, one
result set.

## How many

- **Moderate** — 1 subagent. The point is context isolation, not parallelism.
- **Deep** — 3–4 angles.
- **Exhaustive** — 4–6 per pass, multiple passes.

More subagents than the question has genuine angles produces overlap, not coverage. If you can't name
what makes angle 5 different from angles 1–4, don't dispatch it.

## Per-seed work

When the user supplies a list to enrich — 20 companies, 15 papers — batch **3–5 seeds per subagent**.
One subagent per seed spends more on dispatch overhead than on searching.

## Multi-pass patterns

Some questions can't be parallelized flat, because later work depends on earlier results. Compile and
dedupe **between** passes.

- **Entity chaining.** Pass 1 finds companies; pass 2 finds the relevant people at each; pass 3 finds
  what those people said publicly. Each pass is a round of parallel subagents.
- **Scout then dig.** Pass 1 maps the landscape broadly; pass 2 goes deep on the two or three
  directions that turned out to matter.
- **Criteria discovery.** When "best" isn't defined, pass 1 finds what practitioners actually value;
  pass 2 searches for candidates against those criteria. Don't invent the criteria yourself.

## Before dispatching, decide these

Otherwise subagents return incompatible output and you spend the pass reconciling formats:

1. **The schema.** Exact field names every subagent returns.
2. **Qualification.** What makes a result valid, stated concretely enough that a subagent can filter
   before returning. Filtering at the subagent is far cheaper than filtering after.
3. **The output format.** Compact JSON or a markdown table — pick one and give it to all of them.
4. **The dedupe key.** Usually URL plus entity name.

## After the pass

Overlap between subagents is a **good** sign — it suggests you've saturated the available sources.
Completely disjoint results usually mean an angle was missed, or that one subagent drifted off-topic.
Either way, check before concluding.
