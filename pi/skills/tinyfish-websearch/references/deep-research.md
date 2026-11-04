# Deep research runs

Read this only after the user explicitly asked for deep research; `SKILL.md` has the gate.

1. `start_deep_research` with `query` (the question plus every scope and constraint the user gave,
   dates computed as in `SKILL.md` "Dates first") and `mode`. `deep` is the default; use `max` only when the
   user asks for maximum depth or an exhaustive report — it is slower and costs more. It returns a
   `research_run_id`.
2. `get_deep_research` with that `research_run_id` until the run finishes and the cited report is
   in the result. **Start one run per request**: if you already have a `research_run_id` for this
   question, keep polling it instead of starting another. **Never cancel because it is slow**;
   `cancel_deep_research` is only for when the user asks to stop.
3. Deliver the full report in chat, in `SKILL.md` Step 3's answer shape with its citations as
   inline links; Step 3's one-screen limit doesn't apply. Open with "I used a TinyFish deep research
   run." instead of the sources-and-passes line. Don't redo the research with search passes; one
   `fetch_content` to check a load-bearing claim is fine.

If the deep research tools aren't available, or the run fails, say so and offer the search-and-fetch
passes in `SKILL.md` instead. Never swap one for the other silently.
