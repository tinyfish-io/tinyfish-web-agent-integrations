# Writing goals that work

## The mental model

TinyFish is a capable but literal-minded assistant sitting in front of a browser.

**It can:** see what you'd see on screen, click, type, scroll, navigate, wait for dynamic content,
follow instructions precisely, remember information across steps, read multi-page PDFs, parse natural
language into form fields, and return structured data.

**It cannot:** read your mind about what you meant, guess what to do when something unexpected
happens, know your business context unless you supply it, or decide on an output format you didn't
specify.

Your job is removing ambiguity. Every ambiguity you leave is a decision point where the run can go
somewhere you didn't intend — and a step you paid for.

## Anatomy of a good goal

Seven components. Simple tasks need two or three; complex extractions benefit from all seven.

| Component | Purpose | Example |
|---|---|---|
| Objective | What to achieve | "Extract pricing information" |
| Target | Where to focus | "from the pricing table" |
| Fields | What data to capture | "plan name, monthly price, seat limit" |
| Schema | Output structure | "Return JSON with keys: name, price" |
| Steps | Sequence of actions | "Close the cookie banner first" |
| Guardrails | What **not** to do | "Do not click any purchase buttons" |
| Edge cases | Handle the unexpected | "If price shows 'Contact us', set to null" |

Guardrails and edge cases are the two people skip, and they're where runs go wrong. The agent will do
*something* when it hits an unexpected state; deciding what, in advance, is your job.

## Three quality levels

**Vague — fails:**

```
Get the pricing from this page
```

Annual or monthly? Which plans? What format? The agent doesn't know what "pricing" means to you.

**Better — might work:**

```
Extract the plan name, price, and seat limit. Return as JSON.
```

Clearer, still ambiguous. Multiple prices per plan? What JSON structure? What about enterprise tiers
with no listed price?

**Production-ready:**

```
Extract the following from the pricing table on this page:
- plan_name (exactly as displayed)
- monthly_price (number only, no currency symbol)
- annual_price (number only, null if not shown)
- currency (ISO code)
- seat_limit (integer, null if unlimited)

Close the cookie banner if one appears.
Do not click any Contact Sales or Start Trial buttons.
If a plan shows "Contact us" instead of a price, set both price fields to null.
Ignore add-on products listed below the main table.

Return a JSON array, one object per plan.
```

Every decision point is answered.

## Match style to task type

| Task | Style | Principle |
|---|---|---|
| Price / product extraction | Specific, constrained | List exact fields, exclude everything else |
| Form filling | **Natural language** | Describe the person or entity; let the agent map fields |
| Multi-step workflow | Numbered steps | Enables cross-step memory references |
| Batch execution | Minimal, strict schema | Only essential fields, for consistency across runs |

**Forms are the counter-intuitive one.** Don't enumerate field-by-field instructions — describe the
entity in prose and let the agent do the mapping:

```
Fill out the contact form with this information:

Jordan Lee is a platform engineer at Acme Corp in Denver.
Email jordan.lee@acme.example, phone 303-555-0148.
Interested in the Enterprise plan, wants a demo next week.

Submit the form when complete.
```

The agent maps "platform engineer" to job title, "Acme Corp" to company, and so on. Field-by-field
instructions break as soon as the form's layout differs from your assumption.

**Multi-step workflows use numbered steps** so later steps can reference earlier ones:

```
Complete this workflow:

1. Navigate to the reports section
2. Set the date filter to last 30 days
3. Note the total row count shown (save for later)
4. Export the report as CSV
5. Confirm the download completed

Return the row count from step 3 and the export status.
```

## Extraction: constrain hard

Over-fetching is the most common waste. The agent returning "everything about the product" costs steps
and floods your context.

```
Extract ONLY the following from the pricing table:
- plan_name: string
- monthly_price: number (no currency symbol)
- feature_count: integer

Do not extract feature descriptions or marketing copy.
Return as JSON array.
```

`ONLY` and an explicit exclusion line both pull their weight here.

## Single runs vs. batch

**Single runs** — optimize for completeness. Rich results, detailed edge-case handling, verbose output
you can debug against, because you can iterate.

**Batch runs** — optimize for *consistency*. Every run must return an identical structure, so minimize
fields to exactly what you need and pair the goal with a strict `output_schema`. A field that's
sometimes-present breaks downstream processing across hundreds of runs. Test the goal on one URL
before batching it.

## Costs

Steps are the billing unit: 1 credit per step. Goals that wander cost more than goals that don't.

- **Start the run on the right page.** Passing a homepage `url` and asking the agent to find the
  pricing page spends steps navigating. Pass the pricing URL — use `search` first if you don't know it.
- **Set `agent_config.max_steps`** on exploratory goals so a confused run has a ceiling.
- **Don't automate what you can fetch.** Reading is free.

## Checklist

- [ ] Objective states what "done" means
- [ ] Fields named explicitly, with types
- [ ] Output structure specified, or `output_schema` supplied
- [ ] Guardrails for anything destructive or irreversible on the page
- [ ] Edge cases: missing values, banners, empty states, pagination
- [ ] Starting `url` is as close to the target as possible
- [ ] No credentials anywhere in the goal text
