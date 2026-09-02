# Deployment

## Environments
Prod is live today, deployed to Railway (see commit `eedbdfa`'s "broke the Railway
build"). Three independent sources agree on this, though not in identical wording:
`dashboard/SUMMARY.md` has a `## Status` heading with value `live`, `SECURITY.md`
states "this is live, not a future plan," and `backlog/BACKLOG.md`'s 2026-09-01
entry (in Ukrainian) records the status as changed to `"Працює"` ("Working"/live).
Staging does not exist yet — `infra/staging/` and
`infra/prod/` are still empty placeholders (`infra/README.md`: no IaC tool has been
chosen). The staging+prod split named in `PIPELINE.md` §7 was a bootstrap-time
judgment call, never confirmed by the user and never actually built — treat
"staging" as aspirational, not a real environment, until it exists.

## Deploy Steps
Currently deployed to Railway (PaaS). This is the practice as it actually happened,
reconstructed from the repo, not a pipeline anyone documented before building it —
there is no Railway config file or `Procfile` in this repo, so the real start
command lives in Railway's project settings, not in git:
- **Stack**: Python/Flask (`Flask`, `Flask-SQLAlchemy`, `Flask-Login` — not the
  Node/Next.js stack `PIPELINE.md` Phase 2 records; that phase is stale, the
  shipped code is Flask). Entry point is `src/app.py`'s module-level `app =
  create_app()`. `gunicorn` is pinned in `requirements.txt`, which is consistent
  with it being the WSGI server, but since (as just noted) the real start command
  lives in Railway's project settings and not in git, this repo cannot actually
  confirm gunicorn is what Railway invokes — a pinned dependency proves it's
  installed, not that it's on the command line running in prod. No Python version
  is pinned anywhere either (no `runtime.txt`, `.python-version`, or Railway/
  Nixpacks config), so a from-scratch deploy gets whatever Python version
  Railway's build system currently defaults to, which may not match what this
  was developed against.
- **Database**: `DATABASE_URL` selects Postgres (`psycopg2-binary` is pinned for
  this); unset, it falls back to a local SQLite file (`data/portfolio.db`) — see
  `.env.example`, which frames SQLite as the default and Postgres as something to
  switch to "only if concurrent writes become a real problem." Nothing in this
  repo actually confirms which one prod is running — no `DATABASE_URL` value is
  recorded anywhere, so don't take "Postgres in prod" as settled without checking
  the live Railway service's variables. **If prod is in fact still on the SQLite
  default, this matters a lot**: `data/portfolio.db` is git-ignored (`.gitignore`
  line 25) and lives inside the app's own container. Railway's container
  filesystem is ephemeral — unless a persistent volume is explicitly attached
  (nothing in this repo or `infra/README.md` mentions one), every redeploy can
  silently wipe all users, automations, and ROI data with no warning. This
  repo also doesn't record how many instances/replicas the Railway service
  runs — if it's more than one, that compounds the same risk a second way
  (concurrent writers to two divergent local SQLite files, not just one file
  disappearing on redeploy), so instance count is one more unconfirmed
  variable here, not just the volume question. There is
  also no migration framework (no Alembic/Flask-Migrate): schema is created/
  updated by hand via custom Flask CLI commands in `src/app.py` (`flask init-db`
  for a fresh DB, `flask migrate-registration` for the registration-feature
  columns). A from-scratch or restored DB also has no login path until someone
  runs `flask --app src.app create-user <email> <name> --admin` (`src/app.py`'s
  `create-user` command, per `README.md`) to create the first admin — without
  this step `init-db`/`migrate-registration` alone leave nobody able to log in
  or approve further registrations. All three commands have to be run against
  the prod DB manually to have effect there — that's this doc's own
  characterization of what "run against prod" means, not a phrase used
  anywhere else in the repo (`README.md` documents all three purely as
  local-dev setup steps and never frames them as prod commands at all) — and
  this repo does not say *how* to actually reach the prod DB to run them;
  there's no
  documented `railway run`/shell/SSH mechanism for executing a one-off command
  against the deployed service. `create-user` specifically prompts interactively
  for a hidden, confirmed password (`click.prompt(..., hide_input=True,
  confirmation_prompt=True)`), which needs a real TTY attached to the remote
  process — a plain `railway run flask ... create-user ...` from a local
  terminal is the likely path, but that's an assumption, not something this repo
  documents. One more thing this step produces that whoever runs it needs to
  handle deliberately: `create-user`'s success output is
  `click.echo(f"Created ... (api_key: {user.api_key})")` — it prints the new
  admin's `api_key` in plain text. `README.md` already flags this key as
  printed exactly once with no UI to view or regenerate it, and `SECURITY.md`
  treats any `api_key` as a live credential regardless of source — so running
  this against prod means capturing that terminal output somewhere safe
  before it scrolls away, not just noting that a login now exists.
- **Env vars** (see `.env.example`): none of them make the app fail to start if
  unset — every read in `src/app.py`/`src/github_sync.py`/`src/telegram.py` goes
  through `os.environ.get(...)` with a fallback, not a hard requirement — but they
  aren't equally safe to skip in prod:
  - `ADMIN_TELEGRAM_CHAT_ID` is load-bearing, but not silently: if it's unset,
    `telegram_bot.py`'s `run()` calls `raise SystemExit(...)` and refuses to
    start at all — a loud crash of the approval-bot process, not a quiet
    degradation. And if the bot process *is* up but message delivery still
    fails, `/register` in `src/app.py` flashes a visible warning to the
    registrant ("не вдалося сповістити адміністратора..."), it doesn't swallow
    the failure either. What actually has no visible signal is narrower than
    "the flow silently can't complete": an admin who never notices the bot
    process died has no dashboard-side alert telling them registrations are
    piling up unapproved.
  - `AUTH_SECRET` and `TELEGRAM_BOT_TOKEN` fail *silently* rather than loudly if
    unset: `AUTH_SECRET` falls back to a hardcoded insecure dev key (`src/
    app.py`), and a missing `TELEGRAM_BOT_TOKEN` makes `src/telegram.py` return
    `None` from every call instead of erroring — both are real prod
    requirements even though the code won't tell you they're missing.
  - `DATABASE_URL` and `GITHUB_TOKEN` are genuinely optional: no `DATABASE_URL`
    just means SQLite instead of Postgres; no `GITHUB_TOKEN` just means
    unauthenticated (rate-limited) GitHub API calls in `github_sync.py`.
  - `CLICKUP_API_TOKEN` is listed in `.env.example` but is never read anywhere in
    `src/` (`grep -rn CLICKUP_API_TOKEN src/` matches nothing outside a comment)
    — it does nothing today; don't treat it as required.
- **`src/telegram_bot.py` runs as a separate long-lived process** (polling, not a
  webhook) that must be deployed and kept running alongside the web process —
  shipping only the web app leaves registration approval dead with no error shown
  to the person trying to register. **How that process actually runs on Railway
  today is not documented anywhere in this repo**: there's no `Procfile`, no
  second-service config, no supervisor setup, and the only run command on record
  (`python -m src.telegram_bot`, from `README.md`) is written for local dev. This
  repo cannot say whether prod runs it as a second Railway service, a worker
  process, or isn't running it at all — treat that as unconfirmed, not as "yes,
  it's up."
- **Still genuinely undecided / undocumented**: a real IaC setup for
  `infra/staging`/`infra/prod`; the actual deploy trigger (push-to-`main`
  auto-deploy via Railway's GitHub integration vs. `railway up` vs. a manual
  dashboard click — nothing in this repo says which, see the Rollout Strategy
  hedge below); how `telegram_bot.py` is kept running on Railway (previous
  bullet); which Python version Railway's build actually resolves to (previous
  bullet); whether `gunicorn` (pinned in `requirements.txt`) is actually what
  Railway invokes as the start command, as opposed to just being installed
  (Stack bullet above); whether prod is reachable only through Railway's
  default subdomain or through a custom domain with its own DNS/TLS setup —
  nothing here names either; and which Railway project/workspace this even is — no project name,
  team, or invite process is written down anywhere in this repo, so a newcomer
  following this doc has no way to locate the actual deployment to look at its
  logs or settings without asking someone directly. (One thing that's *not*
  undecided, just unbuilt: there is no CI step ahead of a deploy, confirmed by
  `PIPELINE.md` §7 — no test command exists yet, so a deploy today is not
  blocked on tests passing. That's a settled fact about the current state, not
  an open question.)

## Rollout Strategy
Assumed direct deploy: whatever the actual trigger turns out to be (see "still
undecided" above — this repo doesn't confirm push-to-`main` vs. `railway up` vs.
a manual dashboard click), there's no canary/blue-green step in between — for
the web app, it's just one new Railway deployment replacing the running one.
That framing covers only the web process, though: Deploy Steps above can't
confirm whether `telegram_bot.py` runs as its own second Railway service, a
worker process, or isn't running at all, so if it does run as a separate
service, deploying it is a second, independent deployment event this
single-deployment description doesn't account for. Choosing anything more gradual
isn't meaningful yet since there's no real staging environment to graduate a
rollout through. Change history is *intended* to be tracked via `CHANGELOG.md` +
Conventional Commits, but per `PIPELINE.md` §7 this isn't actually happening yet
— `git tag` returns nothing and `CHANGELOG.md`'s `[Unreleased]` section still
only reads "Initial scaffold," unchanged since the 2026-08-23 initial commit,
despite ~20 real commits since. So a rollback does **not** have the
changelog-based record this might imply. What it does have is plain git history
— but even that is weaker than it sounds: per `git log --oneline`, only 4 of the
22 commits actually carry a `feat:`/`fix:`/`docs:` type prefix (confirmed by
direct count), and neither the most recent commit (`07454a2`) nor the merge
commit (`1b71353`) follow it. A reader scanning `git log --oneline` for the
offending change by its prefix will find 18 of 22 messages don't have one to
scan for — the log is still readable (message text plus timestamps), just not
the tidy prefix-tagged trail this might otherwise imply.

## Rollback
Git revert + redeploy — for application code only. It does **not** cover the
database: schema changes are applied by hand via the `flask migrate-registration`-
style CLI commands above, not through a reversible migration tool, so reverting the
commit that introduced a schema change does not undo it in the running database
(Postgres or SQLite, whichever prod actually is — see Deploy Steps). A rollback
that involves a schema change needs a manual, matching
down-step; no backup process is documented anywhere in this repo yet, so there's
currently no fallback if that manual step goes wrong.

It also does not cover Railway project/service settings (start command, env
vars set in the dashboard, etc.) — as noted in Deploy Steps, those live outside
git entirely. If a bad deploy was actually caused by a settings change rather
than a code change, `git revert` has nothing to revert; whoever changed the
setting has to change it back by hand.

## Post-Deploy Verification
No automated health checks or monitoring exist yet (see `OBSERVABILITY.md`) — and
this is now a real gap, not a bootstrap-time placeholder overtaken by later code:
the app is live in prod without one. Until one exists, verify a deploy manually:
confirm `/login` responds, confirm `telegram_bot.py` is running and an admin
`/grant <email> <role>` command still gets a response in Telegram, check the
app's Railway logs for startup errors, and — because both fail silently rather
than erroring (Deploy Steps above) — confirm `AUTH_SECRET` and
`TELEGRAM_BOT_TOKEN` are actually set to real values in the live Railway
environment, not just present locally in `.env`. If this deploy shipped a
schema change, also confirm the matching `flask migrate-registration`-style
command was actually run against the prod DB; nothing else in this doc's
process re-checks that it was.

**Caveat carried over from Deploy Steps**: none of this is as one-click as the
list above makes it sound. This repo doesn't record the production URL, or the
Railway project/service name, anywhere — so "confirm `/login` responds" and
"check the app's Railway logs" both assume you already know where prod lives,
which (per the workspace-identity gap noted above) you can't get from this repo
alone. Treat these as the right checks to run once you have that access, not as
steps a stranger can follow unaided from this doc.
