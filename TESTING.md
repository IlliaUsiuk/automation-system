# Testing

## Strategy
Unit, integration, and end-to-end tests are all planned: unit for ROI calculation and
data-mapping logic, integration for the API routes against Postgres, and end-to-end
for the core dashboard flows (login, view registry, view an automation's ROI).
Candidate frameworks for a Next.js/TypeScript stack: Vitest or Jest for unit/integration,
Playwright for end-to-end — not yet confirmed, decide once real code exists.

## How to Run
No test command exists yet - no code has been written. Fill this in with the real
`npm run test`/`npm test`-style command once the test framework above is actually
chosen and wired up.

## Coverage
Best-effort — no formal coverage target.

## What's Not Covered Yet
Nothing is covered yet — this is a bootstrap-time doc, no tests exist. CI is not
wired up yet either (see `PIPELINE.md` §7): once a real test command exists, CI should
require it to pass before merge — the project's stated v1 priority is long-term
maintainability over shipping fast, which favors a blocking gate over an advisory one.
