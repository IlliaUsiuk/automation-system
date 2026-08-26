# Development Pipeline — Automation ROI Dashboard

> Generated at bootstrap time from the stage-0-supplax interview. This is a record
> of decisions made, not a generic checklist — a phase with nothing decided yet says
> so honestly instead of showing a placeholder.

```
Intent → Architecture → Build → Test → Security Review → Release → Deploy → Verify → Rollback-Ready
```

## Phase 1 — Intent & Scope
Internal dashboard listing every Supplax automation, its skills/category, ownership,
links (GitHub/ClickUp), and ROI (time/money saved, status). Audience: internal team
only, for both leadership transparency and employee visibility. Private/internal
project. v1 optimizes for long-term maintainability over shipping fast. "Done" for v1
is the registry + ROI cards described in `ROADMAP.md`'s "Now" section — Telegram
alerts and token-usage tracking are explicitly deferred (see `ROADMAP.md` Next/Later).
Value hypothesis and measurement plan: see `dashboard/ROI.md` (full methodology in
`docs/roi_explained.md`). A detailed design pass (including
visual/artifact-style design for the ROI views, and a `PROMPTS.md` staged build plan)
is planned as the next step after this Stage 0 bootstrap — not yet done. Visual
direction the owner already named for that pass: "airy, clean, icon-driven,
Claude-like" — a starting direction for Stage 1's design conversation
(see `PROMPTS.md`), not a finished spec.

## Phase 2 — Architecture & Stack
Stack: Node/TypeScript with Next.js. Data storage: Postgres (relational) — automations,
skills catalog, ownership, ROI metrics. Architecture style: monolith. Expected scale:
medium. Archetype: Dashboard/analytics (see the `src/`, `notebooks/`, `data/`,
`reports/figures/`, `config/`, `tests/` folders this bootstrap created). This early,
hard-to-reverse stack choice is recorded as `docs/adr/0001-stack-and-architecture.md`.

## Phase 3 — Development Workflow
Branching: GitHub flow (feature branches + PR into main). Review: solo for now (just
the one developer). Commit convention: Conventional Commits (pairs with the
`changelog-generator` skill). Outside contributors are expected, so `CODE_OF_CONDUCT.md`
was created.

## Phase 4 — Testing & QA
Planned test types: unit, integration, and end-to-end (see `TESTING.md` for the
candidate frameworks). Coverage expectation: best-effort, no formal target. Test
framework: not yet confirmed — no code exists yet. CI merge gate: not yet decided by
the user explicitly; this bootstrap's judgment call is "required to pass" once a real
test command exists, because the stated v1 priority is long-term maintainability —
revisit this call once the test framework is actually chosen.

## Phase 5 — Security & Compliance
Public attack surface: yes — external (beyond-internal-network) login/access is
planned, so `SECURITY.md` was created. Compliance requirements: not specified by the
user ("you decide"); this bootstrap's judgment call is "none" — no customer/regulated
personal data is currently in scope, only internal automation metadata — revisit if
that changes. Secrets handling: not specified by the user ("do what's right"); this
bootstrap's judgment call is `.env` file, gitignored, for now (`.env.example` created
listing `DATABASE_URL`, `AUTH_SECRET`, `GITHUB_TOKEN`, `CLICKUP_API_TOKEN`,
`TELEGRAM_BOT_TOKEN`) — migrate to a dedicated secrets manager once external access
actually ships.

## Phase 6 — Governance & License
Supplax default applied without asking, per this internal project's own default rule:
license = Proprietary, no public license; copyright holder = Supplax.

## Phase 7 — CI/CD & Release
Deploy target: not yet decided. Environments: not explicitly decided by the user
("you decide"); this bootstrap's judgment call is staging + prod, given external
access and medium scale are both planned — revisit at the design stage. Versioning
scheme: not decided (Conventional Commits + `CHANGELOG.md` are already in place,
which pairs naturally with Semantic Versioning if that gets picked later). CI: not
wired up yet — no test command exists to run, so no CI workflow file was created;
revisit once Phase 4's framework choice lands. Rollout strategy: direct deploy, with
change history tracked via `CHANGELOG.md` + git tags/commits (Conventional Commits)
so a rollback has a real record to work from.

## Phase 8 — Operations & Support
On-call/incident response: not yet, too early — `RUNBOOK.md` was not created.
Support channel: the user wants this handled via Telegram rather than the Supplax
default of ClickUp — exact shape (bot, channel, workflow) is deferred to the design
stage; `SUPPORT.md` reflects this as a placeholder. Monitoring: metrics + alerts, so
`OBSERVABILITY.md` was created.

## Phase 9 — Rollback & Verification
Rollback approach: git revert + redeploy. Post-deploy verification: automated health
checks.

---

*This file reflects the state of decisions as of bootstrap time. As the project
changes, update the relevant phase section directly - `doc-sync` can help keep this
file within its size budget if it grows.*
