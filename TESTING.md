# Testing

## Strategy
The live app (`src/`, ~1,500 lines) is Flask/Python — Flask, Flask-SQLAlchemy,
Flask-Login, psycopg2-binary (see `requirements.txt`) — not the Next.js/TypeScript
stack `ADR-0001` still records as the original plan. (`ARCHITECTURE.md` has
already been corrected to describe Flask — it is not stale; only the ADR
itself still shows Next.js, kept deliberately as a historical record: an ADR
is expected to preserve what was decided at the time, not to track what's
true now, which is a different job from `CONTRIBUTING.md`'s setup steps
flagged near the end of this file — those are actionable instructions a
newcomer actually runs, so a stale stack reference there sends them down the
wrong path instead of just documenting history.) The
datastore is SQLite by default (`data/portfolio.db`, zero config) with
Postgres as an opt-in upgrade via `DATABASE_URL` (`ARCHITECTURE.md`,
`src/app.py`) — not Postgres-by-default, so tests shouldn't assume a Postgres
fixture is required. Testing strategy has to follow the code that actually
exists, not either stale premise:
- **Unit** — pure, no-mocking-needed logic, in two places: `src/models.py`'s
  small helpers (`Role.label`/`Status.label`/`dot_color`, `hue_for`,
  `User.is_admin`/`is_automator`/`can_manage`/`initials`,
  `Department.pill_style`), and — the bigger target by line count, and the
  cheapest to cover well since none of it needs mocking — `src/github_sync.py`'s
  markdown-parsing functions (`parse_readme`,
  `parse_markdown_sections`, `parse_functions_md`,
  `summary_fields_from_sections`, `parse_pages_section`, `parse_backlog_md`,
  `parse_todo_md`, `roi_fields_from_sections`, `parse_skill_md`): each takes a string in and
  returns data out, with no GitHub API call anywhere in them, so they're
  ideal unit-test candidates that need zero mocking. (There's no dedicated
  ROI-calculation method anywhere in the code — `ROIEntry` in
  `src/models.py` is a plain data record with no computed fields; the "ROI"
  logic worth testing is this parsing, which fills that record from a
  repo's markdown.) The app's Flask CLI commands (`src/app.py`: `init-db`,
  `create-user`, `migrate-registration`, `seed-demo`) belong on this list
  too and are currently untested — `migrate-registration` especially:
  it's idempotent and introspects existing columns before altering
  anything, exactly the deterministic, no-network shape this bullet is
  about, just packaged as a CLI command instead of a plain function.
- **Integration** — Flask routes in `src/app.py` against a disposable SQLite
  database (an in-memory `sqlite:///:memory:` or a temp-file DB per run — no
  Postgres server needed for this). Watch out: `create_app()` (`src/app.py`)
  takes no test-config argument and reads `DATABASE_URL` from the
  environment at call time, defaulting to the real `data/portfolio.db` file
  when unset — a fixture has to set `DATABASE_URL` (or otherwise override
  `SQLALCHEMY_DATABASE_URI`) *before* calling `create_app()`, or an
  integration test silently reads/writes the actual local dev database.
  This ordering requirement comes from `create_app()`'s own code, not from
  whichever test framework ends up wrapping it, so it holds regardless of
  the still-open `pytest` vs. something-else decision below.
  Separately, the parts of the two external integrations that actually hit
  the network need faking with `unittest.mock` (patch the functions
  themselves) rather than being hit for real: GitHub sync's
  `fetch_latest_commit` / `default_branch` / `fetch_raw_file`
  (`src/github_sync.py` — not the parsing functions above, which don't touch
  the network) and the Telegram bot approval/registration flow
  (`src/telegram_bot.py`, `src/telegram.py`) — a fabricated GitHub commit
  JSON response, and a fabricated Telegram API payload. Don't reach for the
  `responses` library here: both `github_sync.py` and `src/telegram.py`
  say in their own docstrings that they use stdlib `urllib.request`
  exclusively, never `requests`, and `responses` only intercepts
  `requests`-based traffic — pointed at this codebase it would silently
  intercept nothing rather than fake anything.
  The most branch-heavy piece of logic worth its own dedicated integration
  scenarios, not just "fake the network and move on," is
  `sync_automation_from_github` in `src/app.py` (and the `POST
  /api/automations/<slug>/sync` endpoint that also calls it): it holds
  every clear-vs-preserve decision for a re-sync (`ARCHITECTURE.md` — e.g.
  an empty `## Pages` section only clears stale pages when `SUMMARY.md` was
  actually fetched), so it needs cases for each of those branches, not just
  one happy-path fetch.
  Most authenticated routes worth integration-testing sit behind
  `@login_required`/`@automator_required`, but the only account-creation
  path this doc or `README.md` documents is the `create-user` CLI, which
  README flags as interactive-only (hidden, confirmed password prompt —
  "don't expect to script it without a pty"). For tests, create a user
  directly the same way `create-user` does internally: `User(...,
  is_confirmed=True, is_approved=True)` plus `user.set_password(...)`
  (`src/app.py`'s `create_user` command, `src/models.py`) — no CLI, no TTY,
  no prompt.
- **End-to-end** — core dashboard flows: login, view registry, view an
  automation's ROI. A freshly bootstrapped instance has an empty registry
  (see "How to Run" below), so this needs at least one automation added or
  seeded first — via the manual "add automation" form or README's
  `seed-demo` CLI command — or the "view an automation's ROI" step has
  nothing to click on. Registration/approval is only partly E2E-testable
  this way: the confirmation-code step runs in-app, but completing approval
  needs an admin's Telegram `/grant` reply, which requires
  `src/telegram_bot.py` running as its own long-lived process (see
  `DEPLOYMENT.md`) — either fake that Telegram round-trip the same way
  Integration does, or treat the admin-approval half as a manual check
  rather than a true automated E2E step.

Candidate frameworks: `pytest` (+ `pytest-flask`) for unit/integration,
Playwright for end-to-end (it drives a running server over HTTP, independent
of the server-side template stack) — not yet confirmed, decide before writing
the first test. Neither is in `requirements.txt` yet; adding it and
`pip install`-ing it is part of that decision, not a separate later step.

Deciding the exact fixture/teardown mechanics for that disposable database
(temp file vs. `:memory:`, per-test vs. per-run) is part of the same
decision as the framework choice above — see the Integration bullet for the
underlying fact (SQLite, no Postgres server needed); not repeated here.

## How to Run
No test command exists yet — this is the gap to close, not a placeholder for a
future codebase: `src/` is real, working, and already deployed (`dashboard/
SUMMARY.md` status: live), it simply has zero automated tests today. Fill this
in with the actual run command once the framework above is chosen and wired
up; new test files belong in `tests/` (`tests/README.md` already names this
section as its pair).

Until then, the only way to verify a change is manual: follow root
`README.md`'s "Install" and "Usage" sections to get a local copy running
(`python -m src.app` for the web app, plus `python -m src.telegram_bot` in a
second process — registration approval needs both). Don't use `src/README.md`
for this: it's a one-paragraph note on what belongs in that folder, with no
run steps. `DEPLOYMENT.md` covers the Railway/prod deploy specifically, not
local running — but it still documents general app behavior that applies
locally too, which is why it's cited below for the `ADMIN_TELEGRAM_CHAT_ID`
failure mode: that's a fact about the app, not about Railway. Set `TELEGRAM_BOT_TOKEN` and `ADMIN_TELEGRAM_CHAT_ID` in `.env` first (see
`.env.example`; `AUTH_SECRET` can stay unset locally, and so can
`GITHUB_TOKEN` — per `DEPLOYMENT.md` it's "genuinely optional," its absence
just means unauthenticated, rate-limited GitHub calls, nothing that blocks
this walkthrough). Without `ADMIN_TELEGRAM_CHAT_ID` specifically, the
failure is loud, not silent: `telegram_bot.py`'s `run()` calls `raise
SystemExit("ADMIN_TELEGRAM_CHAT_ID не задано в .env")` the instant you
launch that second process (above), so the whole approval-bot process refuses
to start with a printed error rather than quietly doing nothing
(`DEPLOYMENT.md` says the same once you read past its first bullet — its
next bullet contrasts this with `AUTH_SECRET`/`TELEGRAM_BOT_TOKEN`, which
*do* fail silently). If instead the bot process is running but an admin
never gets a Telegram message, suspect a missing `TELEGRAM_BOT_TOKEN`:
`src/telegram.py` returns `None`/`False` from every call when it's unset,
with no error at all — that's the actually-silent failure mode.

Then, before any of that is clickable: create the schema (`flask --app src.app init-db`) and the first
account, since self-service registration needs an existing admin to approve
it (`flask --app src.app create-user <email> <name> --admin`, interactive
password prompt) — both are in README's "Usage" section but easy to miss if
this file is followed on its own. Optionally, `flask --app src.app seed-demo
<owner_email>` fills the registry with sample data so there's something to
view (a fresh instance otherwise has zero automations). Then click through
login, registration, and the registry/ROI views by hand.

## Coverage
No coverage tooling or target exists yet — there are no tests to measure. Once a
framework is chosen, decide a target rather than assuming "some tests" already
implies a coverage practice.

## What's Not Covered Yet
Nothing is covered yet — this is a bootstrap-time doc, no tests exist. That's a
different risk than "no code exists yet": the live app already serves login
and self-service registration reachable by anyone who hits `/register`, not
just Supplax employees — access is gated by admin approval *after* signup,
not by who can submit a request in the first place. `SECURITY.md`'s Status
section is explicit that this makes `/register` public attack surface, and
retracts an earlier "audience stays internal-only" framing as stale for the
same reason (`dashboard/SUMMARY.md` agrees: "Завести акаунт може будь-хто" —
anyone can create an account). With zero automated coverage today on exactly
that surface, closing this gap is a near-term priority, not a
someday-bootstrap item. That's a different axis than the Strategy section's
"cheapest to cover well" framing for the markdown parsers above: this is
about risk (public, unauthenticated attack surface with no coverage at all),
that was about cost (pure functions, zero mocking). If only one thing gets
tests first, write registration/`/register` tests first — the parsers are
cheaper, not more urgent.

CI is not wired up yet either (see `PIPELINE.md` §7): once a real test command
exists, CI should require it to pass before merge — the project's stated v1
priority is long-term maintainability over shipping fast, which favors a
blocking gate over an advisory one. Note that a pass/fail gate alone only
enforces that tests exist and pass, not their depth — deciding the (still
unset) coverage target from the section above is a separate, later decision
that the gate doesn't substitute for.

Separately: `CONTRIBUTING.md` and `README.md` don't yet mention running tests as
part of the contribution workflow — once a command exists here, that should be
added there too (out of scope for this file to fix). Worse, and also out of
scope here: `CONTRIBUTING.md`'s "Local dev setup" still tells a newcomer to
install Node.js/npm and links `docs/getting-started.md`, which is entirely
`npm install`/`npm run dev` instructions for the abandoned Next.js stack —
both need the same Flask/Python correction this file just got, or a stranger
sets up the wrong toolchain before ever reaching the test suite.
