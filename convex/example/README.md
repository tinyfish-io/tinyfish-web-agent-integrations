# Example app

A small Convex backend that uses the TinyFish component the way a real app
would:

- [`convex/convex.config.ts`](convex/convex.config.ts) installs the component
  and passes it the API key.
- [`convex/example.ts`](convex/example.ts) wraps each call in an app function
  that checks the caller, records who owns each job, and saves a cited brief
  when a research job finishes.
- [`convex/example.test.ts`](convex/example.test.ts) tests those functions
  with `convex-test` and a stubbed `fetch`.

## Run it

From the package root (`convex/` in this repository):

```sh
npm install
npx convex dev --once
npx convex env set TINYFISH_API_KEY your-key
npx convex dev
```

The functions require a signed-in user. To try them from the Convex dashboard,
use "Act as a user" in the function runner, or replace `requireUser` in
[`convex/auth.ts`](convex/auth.ts) with your auth provider's check.
