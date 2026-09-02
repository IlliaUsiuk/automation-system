# Development Pipeline — Automation ROI Dashboard

> Generated at bootstrap time from the stage-0-supplax interview. This is a record
> of decisions made, not a generic checklist — a phase with nothing decided yet says
> so honestly instead of showing a placeholder.

```
Intent → Architecture → Build → Test → Security Review → Release → Deploy → Verify → Rollback-Ready
```

> Note: this 9-stage diagram is a conceptual pipeline, not a 1:1 index into the 9
> phase headings below — they don't line up positionally. Governance/License is
> Phase 6 (the diagram's position 6 says "Release"); the diagram's "Release" and
> "Deploy" stages are both covered together in Phase 7 ("CI/CD & Release"); the
> diagram's "Verify" stage is covered in Phase 9 ("Rollback & Verification") rather
> than Phase 8 ("Operations & Support"). Read phases by their own titles, not by
> counting positions against the diagram above.

## Phase 1 — Intent & Scope
Internal dashboard listing every Supplax automation, its skills/category, ownership,
links (GitHub/ClickUp), and ROI (time/money saved, status). Audience: internal team
only, for both leadership transparency and employee visibility. Private/internal
project. v1 optimizes for long-term maintainability over shipping fast. **This
audience framing is about who ends up with an account, not who can reach the
endpoint** — see Phase 5's correction below: the shipped `/register` route itself is
reachable by anyone, gated by admin approval after signup rather than by who's allowed
to submit the form.

**Status update (2026-09-02): scope has moved past this phase's original bootstrap
description, and `ROADMAP.md`/`PROMPTS.md` have not been reconciled with the code yet —
treat those two docs' "Now/Next" and "Stage" framing as stale until someone updates
them.** What's actually shipped, per `git log`, well beyond the original "registry +
ROI cards" v1 line: self-service registration with Telegram-based admin approval
(`src/telegram_bot.py`, gated on `ADMIN_TELEGRAM_CHAT_ID`), an Automator role, and the
templates that go with them (`register.html`, `automator_profile.html`,
`departments.html`, `skills_library.html`). Note this is a *different* registration
mechanism than the GitHub-based one `ROADMAP.md`'s "Next" section describes (a worker
self-registering their automation's access via GitHub) — but that item isn't purely
future work either: `POST /api/automations/<slug>/sync` (authenticated per-user via
`User.api_key`, hit by the `automation-portfolio-sync` skill) already creates a
brand-new `Automation` row from scratch when the slug doesn't exist yet
(`api_sync_automation` in `src/app.py`), and `ARCHITECTURE.md`'s own Data Flow section
calls this "live today, not future work." The employee-registration flow itself is two
stages, not one: `/register` sends a confirmation code straight to the admin's Telegram
via `src/telegram.py` (independent of whether `telegram_bot.py` is running — see Phase 2),
the registrant confirms that code at `/confirm`, and only then can the admin's
`/grant <email> <role>` (role: `admin`, `automator`, or `viewer` — README.md) actually
grant access; "gated by admin approval after signup" elsewhere in this document is
shorthand for that whole sequence, not a single step. `ROADMAP.md`'s "Next" bullet needs a rewrite
for the same reason its sibling above does, and `GLOSSARY.md`'s "Skill (registry
field)" entry is now stale too — it still calls this "a future registration tool for
this project itself, not a registry entry," directly contradicted by `ARCHITECTURE.md`'s
own present-tense account (a `GLOSSARY.md` fix, out of scope here, same as
`CONTRIBUTING.md` below). These stay two genuinely distinct features regardless — a
person getting a dashboard account vs. an automation's metadata being pushed into the
registry — don't read one as superseding or explaining away the other; both have just
separately already shipped. The visual/artifact-style design
pass this phase called "not yet done" is also already partly done: `design/` holds
finished Claude-Design canvas artboards (`Main.dc.html`, `Detail.dc.html`,
`Sidebar.dc.html`, `Skills.dc.html`). Value hypothesis and measurement plan: see
`dashboard/ROI.md` (full methodology in `docs/roi_explained.md`). Visual direction the
owner named at bootstrap: "airy, clean, icon-driven, Claude-like" — worth checking
against what `design/` actually produced.

## Phase 2 — Architecture & Stack
**Superseded — this section no longer matches the code and needs an ADR-0002, not just
a prose fix.** Bootstrap originally chose Node/TypeScript + Next.js + Postgres, recorded
in `docs/adr/0001-stack-and-architecture.md`. The project has since built on Flask
instead (`requirements.txt`: Flask, Flask-SQLAlchemy, Flask-Login, gunicorn; `src/app.py`,
`models.py`, `github_sync.py`, `telegram_bot.py`, Jinja templates), with SQLite as the
default datastore (`data/portfolio.db` per `.env.example`) and Postgres kept as an
optional upgrade path via `DATABASE_URL` "only if concurrent writes become a real
problem," not as the primary store. No ADR records this reversal — `ADR-0001` and
`CONTRIBUTING.md`'s "Local dev setup" still describe the abandoned Node/Postgres stack,
and `CONTRIBUTING.md`'s version is actionable: a newcomer following it (`npm install`,
Postgres) hits a dead end, since there is no `package.json` in this repo.
`CONTRIBUTING.md` also links `docs/getting-started.md` for the details, which repeats
the identical stale Node/npm/Postgres/`npm run dev` instructions rather than fixing
them — neither is the doc to send someone to. `README.md` already has the correct,
current setup (venv, `pip install -r requirements.txt`, `.env`, `flask init-db`,
`create-user`); that's the one to point a newcomer at until `CONTRIBUTING.md` and
`docs/getting-started.md` get fixed (both out of scope for this pass). **Correction:
`ARCHITECTURE.md` is not one of the stale files** — a prior draft of this phase said it
was, but the file itself already documents the Flask/SQLAlchemy/Flask-Login/SQLite stack
in detail (routes, roles, GitHub sync, Telegram bot) and its own "Key Decisions" section
already marks ADR-0001 "Superseded in practice." It's the one doc in this cluster that's
already correct; don't send a future reader there to "fix" it. Architecture style:
monolith in the sense of one deployable Flask app, but note `src/telegram_bot.py` is a
separate long-lived polling process — two processes in practice, not strictly one.
**Its role is narrower than earlier drafts of this section implied**: the confirmation
code that kicks off registration is sent directly from the `/register` route via
`src/telegram.py`'s own HTTPS call to the Telegram API, and fires whether or not
`telegram_bot.py` happens to be running (README.md). The bot process is only what
turns a confirmed signup into actual access — an admin's `/grant`/`/revoke` reply is
handled exclusively by `telegram_bot.py`'s polling loop — so it's required for anyone
past the first admin to ever log in, but not for the earlier signup/confirmation steps
to work (see `DEPLOYMENT.md`). Expected scale: medium. Archetype: Dashboard/analytics (see the `src/`,
`notebooks/`, `data/`, `reports/figures/`, `config/`, `tests/` folders this bootstrap
created — that part still holds). Action needed: write `docs/adr/0002-stack-revision.md`
recording the Flask/SQLite switch and why, then update `ADR-0001` and `CONTRIBUTING.md`
to match (`ARCHITECTURE.md` needs no such update) — out of scope for this pass since
those are separate files. Whoever writes ADR-0002 shouldn't start from a blank page,
though: `APP-BUILD-BRIEF.md` already documents this exact decision set with rationale
(Flask over FastAPI/Django, SQLAlchemy, SQLite-first with Postgres as an upgrade path,
Jinja2 over a JS framework, Flask-Login), and its data-model draft names `User`,
`Automation`, `ROIEntry`, `Comparison`, `FeatureRow`, `Connection`, and
`ReviewLogEntry` — the same classes `src/models.py` actually defines. ADR-0002 can
largely transcribe it rather than re-deriving it. That brief is itself stale in one
respect worth flagging while we're here, though not fixing: its header still reads
"Статус: не готові починати білд" ("not ready to start the build"), gated on
hosting/DB blockers that were resolved once the app actually shipped to Railway — the
most stale status line in the repo, and one this pass would otherwise have missed
entirely. Until `CONTRIBUTING.md` is fixed, the actual way to get a working local
database is `flask init-db` (fresh DB) or `flask migrate-registration` (add the
registration columns to an existing one) — see `DEPLOYMENT.md`, not `CONTRIBUTING.md`.
Neither command alone gets anyone logged in, though: `flask --app src.app create-user
<email> <name> --admin` (per `README.md`/`DEPLOYMENT.md`) is the step that actually
creates the first account — skip it and there's a schema with nobody able to sign in
or approve registrations. None of this is reachable without actually starting the app
either (`python -m src.app`, per `README.md`) — omitted from earlier drafts of this
section, which stopped at schema/account creation and left no route to a login page at
all. Optionally, `flask --app src.app seed-demo <owner_email>` populates the registry
with sample ROI data afterward, since a fresh instance otherwise has zero automations to
look at. Separately, no Python version is pinned anywhere in the repo (no
`runtime.txt`/`.python-version` — `README.md` flags this too), so a from-scratch setup
gets whatever Python 3 happens to be on the machine or in Railway's build image.

## Phase 3 — Development Workflow
Branching: GitHub flow (feature branches + PR into main). Review: solo for now (just
the one developer, self-merge is fine). Commit convention: Conventional Commits was the
bootstrap-time intent (pairs with the `changelog-generator` skill), but **in practice
only 4 of the 22 commits in `git log` actually use a `type:` prefix** (2x `feat:`, 2x
`docs:`, zero `fix:` anywhere in the 22) —
the rest, including the most recent one, don't follow it. (`DEPLOYMENT.md`'s own Rollout
Strategy section already says the same thing, in the same terms — it is not a doc that
needs correcting on this point; an earlier draft of this section claimed a contradiction
here that didn't exist against the actual text of that file.) That most recent commit also
added a repo-specific rule to this repo's `CLAUDE.md`: commit subject lines here are
written in Ukrainian, not English, because this automation's own dashboard card
displays its literal last commit subject live (`src/github_sync.py`'s
`fetch_latest_commit`, shown in `automation_detail.html`). That rule and "Conventional
Commits" (an English-keyword convention) haven't been reconciled — treat Conventional
Commits as aspirational/partially-followed, not the settled convention this repo
actually uses, until someone decides how (or whether) a Ukrainian subject line can still
carry a `feat:`/`fix:`/`docs:` prefix. "Outside contributors are expected" here means
other Supplax employees who might join this internal tool later, not public/external
contributors — this is a Proprietary, no-public-license repo (Phase 6) for an
internal-only audience (Phase 1), so `CODE_OF_CONDUCT.md` and `CONTRIBUTING.md` are
scoped to that possibility, not to open-source contribution. Not yet decided: what
happens to solo self-merge once a second Supplax contributor actually shows up (who
reviews PRs, does self-merge still apply) — revisit when that happens instead of
guessing now.

## Phase 4 — Testing & QA
Planned test types: unit, integration, and end-to-end (see `TESTING.md` for the
candidate frameworks — that doc is already corrected for the real stack, not the
abandoned Node/Next.js one from Phase 2: it recommends `pytest` + `pytest-flask` for
unit/integration and Playwright for end-to-end; Vitest/Jest don't appear in it. An
earlier draft of this section claimed otherwise — that was stale against `TESTING.md`
itself, not a gap in that file). Coverage expectation: best-effort, no formal target.
Test framework: not yet confirmed (candidates named, not locked in). **Correction: the original "no code exists yet" premise is no longer true**
— `src/app.py`, `models.py`, `github_sync.py`, `telegram_bot.py`, and a dozen Jinja
templates already ship real functionality (registration, ROI cards, GitHub sync,
Telegram approval), while `tests/` still holds only a placeholder README with zero
actual tests. The real gap this phase needs to close is a shipped, untested codebase,
not an absence of code to test. CI merge gate: not yet decided by the user explicitly;
this bootstrap's judgment call is "required to pass" once a real test command exists,
because the stated v1 priority is long-term maintainability — revisit this call once
the test framework is actually chosen. Worth naming plainly: Phase 1's "maintainability
over shipping fast" is a stated priority, not yet a practiced one — zero tests, no CI,
no git tags, and a `CHANGELOG.md` still reading "Initial scaffold" after 22 commits
(Phase 7) describe a shipping pattern closer to the opposite. Not a reason to change the
stated priority, just a gap between the stated priority and current practice that
whoever picks up Phase 4/7 next should know about going in.

## Phase 5 — Security & Compliance
**Correction (2026-09-02): this phase's "planned" framing is stale — external access has
already shipped.** The original text said external (beyond-internal-network) login/
access "is planned," reconciled as "employees authenticating remotely, audience stays
internal-only, only the network perimeter isn't trusted." `SECURITY.md` itself now
corrects this: the login/registration flow and Telegram approval bot are "built and in
production use" (`dashboard/SUMMARY.md`'s `Status: live`, `backlog/BACKLOG.md`'s
2026-09-01 entry), and — more than a perimeter question — registration itself is
self-service and reachable by anyone who hits `/register`, gated by admin approval
*after* signup rather than by who can submit a request. `SECURITY.md` says to treat
`/register` as public attack surface, not merely "employees connecting remotely."
Compliance requirements: not specified by the user ("you decide"); this bootstrap's
judgment call was "none" — no customer/regulated personal data in scope, only internal
automation metadata. **That judgment needs revisiting, not just noting**: Phase 1's
shipped self-service registration now collects employee personal data (name, email,
department, skills — `register.html`, `automator_profile.html`, `departments.html`,
`skills_library.html`), which is a different fact pattern than "internal automation
metadata only." Whether that triggers any actual compliance obligation is undecided —
flagging it as unresolved rather than re-asserting "none" is the honest state here.
Secrets handling: not specified by the user ("do what's right"); this bootstrap's
judgment call is `.env` file, gitignored, for now (`.env.example` created listing
`DATABASE_URL`, `AUTH_SECRET`, `GITHUB_TOKEN`, `CLICKUP_API_TOKEN`,
`TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_CHAT_ID` for the registration-approval bot) —
originally deferred to "once external access actually ships," but per the correction
above that has already happened, so migrating to a dedicated secrets manager is a
present-tense revisit, not a future trigger. `SECURITY.md` separately flags that
`AUTH_SECRET` has a silent insecure fallback in `src/app.py` if the env var is unset —
worth checking against what's actually configured in the live Railway environment.

## Phase 6 — Governance & License
Supplax default applied without asking, per this internal project's own default rule:
license = Proprietary, no public license; copyright holder = Supplax.

## Phase 7 — CI/CD & Release
**Correction: "Deploy target: not yet decided" is stale — it's already decided and
live.** `DEPLOYMENT.md` records the app deployed to and running in production on
Railway (see commit `eedbdfa`'s "broke the Railway build"; `dashboard/SUMMARY.md`,
`SECURITY.md`, and `backlog/BACKLOG.md`'s 2026-09-01 entry all say `Status: live`).
There is no Railway config file or `Procfile` in this repo — the real start command
lives in Railway's project settings, not in git — so `DEPLOYMENT.md`, not this file, is
the source of truth for deploy mechanics. Also missing from every doc, this one
included: the actual live URL/domain. `DEPLOYMENT.md`'s Post-Deploy Verification
section says to check that `/login` responds without naming the host to check it
against, and `APP-BUILD-BRIEF.md`'s `supplax.ai`/`portfolio.supplax.ai` domain was an
aspirational pre-Railway VPS plan, never confirmed as what's actually live now —
whoever picks up Phase 7/8/9 work next should record the real host somewhere.
Environments: **also stale** — this phase
called staging + prod a still-open bootstrap judgment call to "revisit at the design
stage," but `DEPLOYMENT.md` is blunter: that split "was never confirmed by the user and
never actually built," `infra/staging/` and `infra/prod/` are empty placeholders, and no
IaC tool has been chosen (`infra/README.md`). Treat "staging" as aspirational, not a
real environment, until it exists. Versioning scheme: not decided (Conventional Commits
+ `CHANGELOG.md` are nominally in place, though see Phase 3's correction — only 4 of 22
commits actually follow the Conventional Commits format, which weakens how cleanly
`changelog-generator` can derive a version bump from history today). CI: not wired up
yet — no test command exists to run, so no CI workflow file was created; revisit once
Phase 4's framework choice lands. A deploy today is not blocked on tests passing. Rollout
strategy: direct deploy (a push to `main` becomes a new Railway deployment, no canary/
blue-green — not meaningful yet with no real staging to graduate through), with change
history intended to be tracked via `CHANGELOG.md` + git tags/commits (Conventional
Commits) so a rollback has a real record to work from. **This isn't actually happening
yet**: `git tag` currently returns nothing, and `CHANGELOG.md`'s `[Unreleased]` section
still only reads "Initial scaffold" despite 22 commits since (only 4 of which use a
`feat:`/`docs:` prefix — zero use `fix:` — see Phase 3). The rollback plan in Phase 9 depends on this
record existing — until someone tags releases and keeps `CHANGELOG.md` current (the
`changelog-generator` skill can do this from Conventional Commits, once commits actually
follow that format), Phase 9's "revert + redeploy" has nothing concrete to revert to.

## Phase 8 — Operations & Support
On-call/incident response: not yet, too early — `RUNBOOK.md` was not created.
Support channel: the user wants this handled via Telegram rather than the Supplax
default of ClickUp — exact shape (bot, channel, workflow) is deferred to the design
stage; `SUPPORT.md` reflects this as a placeholder. Monitoring: metrics + alerts were
the bootstrap-time intent, so `OBSERVABILITY.md` was created — **but per that file
itself, nothing is actually instrumented: "Nothing yet — no code exists," no
dashboards, no alerts, no token-usage tracking.** This was a reasonable placeholder at
bootstrap time; it no longer is, now that the app is live in production (Phase 7,
`DEPLOYMENT.md`) with zero automated health checks. `DEPLOYMENT.md` calls this out as
"a real gap, not a bootstrap-time placeholder overtaken by later code" and documents
the current manual fallback (check `/login` responds, confirm `telegram_bot.py` is
running, check Railway logs). Treat this as a live operational gap on a running system,
not a future nice-to-have to revisit whenever convenient.

## Phase 9 — Rollback & Verification
Rollback approach: git revert + redeploy — **for application code only, and even that
side isn't as solid as this phrasing implies.** Phase 7 already found `git tag`
returning nothing and `CHANGELOG.md` unmaintained since "Initial scaffold" — so there's
no tagged, changelog-backed point to revert *to* yet either; "revert + redeploy" is a
plan with nothing concrete behind it right now, not just a plan that stops short of
covering the database. Per `DEPLOYMENT.md`, it doesn't cover the database either: there
is no migration framework (no Alembic/Flask-Migrate), schema changes are applied by hand
via `flask
migrate-registration`-style CLI commands with no reversible down-step, and no backup
process is documented anywhere in this repo. A revert that undoes a commit which
introduced a schema change does **not** undo that change in the running database
(Postgres or SQLite — per Phase 2/`DEPLOYMENT.md`, nothing in this repo actually confirms
which one prod is running, so don't read this as Postgres being settled) — a rollback
touching schema needs a manual, matching down-step, with no documented fallback if that
goes wrong. Post-deploy verification: automated health
checks was the bootstrap-time intent, but per Phase 8/`OBSERVABILITY.md` none exist yet
— today verification is manual (see `DEPLOYMENT.md`'s Post-Deploy Verification
section).

---

*This file reflects the state of decisions as of bootstrap time. As the project
changes, update the relevant phase section directly - `doc-sync` can help keep this
file within its size budget if it grows.*

*Last verified against the actual repo: 2026-09-02. Round 1 found Phase 2's stack and
part of Phase 1's status stale. Round 2 (this pass) found more: Phase 2 had also
wrongly named `ARCHITECTURE.md` as stale (it isn't — it's already self-correcting);
Phase 3's Conventional Commits claim doesn't match actual git history and hasn't been
reconciled with the new Ukrainian-commit-subject rule in this repo's `CLAUDE.md`; Phase
5's "external access is planned" was stale against `SECURITY.md`'s own live-status
correction, and Phase 5's compliance judgment ("no personal data in scope") needed
reopening now that self-service registration collects real employee personal data;
Phase 7's deploy target and staging/prod environments were stale against
`DEPLOYMENT.md`; and Phase 8/9 understated the live production risk of having zero
monitoring and no database rollback path (nor a working application-code rollback path,
for that matter — see Phase 9's updated tag/`CHANGELOG.md` caveat).

*Further verification (this pass) found errors introduced by Round 2 itself, not just
carried over from bootstrap: Phase 3 had fabricated a contradiction with `DEPLOYMENT.md`'s
Rollout Strategy section (that section actually agrees with Phase 3's own 4-of-22 count,
word for word in substance) and misnamed which two prefixes make up those 4 commits
(`feat:`/`docs:`, never `fix:` — Phase 7 had also inherited that same misnaming, now
fixed); Phase 4 had claimed `TESTING.md` still recommended Vitest/Jest/Playwright for the
abandoned Node stack when that file was already corrected to `pytest`/Playwright; Phase 9
had dropped Phase 2's own Postgres-vs-SQLite hedge and asserted Postgres as the settled
prod database, which neither Phase 2 nor `DEPLOYMENT.md` actually commits to; and Phase
1/2's account of the registration-approval mechanism overstated `telegram_bot.py`'s role
(the confirmation-code step runs independently of it via `src/telegram.py`) while omitting
the confirm-code stage, the `viewer` role, and — in Phase 2's local-setup sequence —
actually starting the app server. Lesson repeated from Round 2: a correction pass has to
re-verify its own cited quotes and counts against the actual files, not just against the
previous round's prose.*

*When any phase here disagrees with what's
actually in the code (or in `SECURITY.md`/`DEPLOYMENT.md`/`OBSERVABILITY.md`, which have
started correcting themselves faster than this file has), **the code wins** — this
file, the ADRs, and `ARCHITECTURE.md` are a record of decisions, not a substitute for
checking `src/`, `requirements.txt`, and `git log` directly.*
