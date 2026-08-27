# Telegram Failure Alerts — Implementation Plan

The detailed companion to `ROADMAP.md`'s "Telegram alerts when an automation
breaks/fails" (Next) and `OBSERVABILITY.md`'s `## Alerts` section — both just
name the feature, this is the actual how. Decided: a **push model** — each
automation's own code reports its own failure to this dashboard, which then
relays to Telegram. A heartbeat/pull model (automations ping "I'm alive" on a
schedule, dashboard alerts on a missed ping) was considered and explicitly
deferred — it catches silent crashes push can't, but needs a scheduler wired
into every automation regardless of whether anything ever breaks. Revisit only
if push alerts turn out to miss too many silent deaths in practice.

Three phases, each blocking the next. `.env.example` already has a
`TELEGRAM_BOT_TOKEN` placeholder waiting for phase 1.

## Phase 1 — Foundation in this repo

Nothing in phase 2 or 3 works without this existing first.

- Create a Telegram bot via [@BotFather](https://t.me/BotFather), get its bot
  token, put it in `.env` as `TELEGRAM_BOT_TOKEN` (the placeholder already
  exists in `.env.example`).
- Decide the alert destination: one shared alerts chat/channel (simplest — one
  `chat_id` to configure once) vs. a personal `chat_id` per automation owner
  (needs a new `User.telegram_chat_id` column, and each owner has to DM the
  bot once to obtain their own `chat_id`). Start with the shared channel;
  per-owner routing is a real but separate follow-up, not a blocker for v1.
- New `Automation` model fields: `last_failure_at` (DateTime),
  `last_failure_message` (Text) — so a failure is visible on the automation's
  own card, not only pushed to Telegram and then forgotten.
- New endpoint `POST /api/automations/<slug>/report-failure`, authenticated
  the same way the existing push-sync endpoint already is — `X-API-Key`
  header matched against `User.api_key` (see `src/app.py`'s
  `api_sync_automation`, the endpoint at `/api/automations/<slug>/sync`, for
  the exact pattern to copy). Body: `{"message": "..."}`. On a valid request:
  write the two new fields, then call Telegram's `sendMessage` Bot API with
  the automation's name and the message.
- Manual end-to-end test: `curl` the new endpoint with a real `api_key`,
  confirm the message actually lands in the Telegram chat.

### Prompt to kick this off
> Implement phase 1 of `docs/telegram_alerts_plan.md` in this repo: add
> `Automation.last_failure_at`/`last_failure_message` to `src/models.py`, add
> a `POST /api/automations/<slug>/report-failure` endpoint to `src/app.py`
> authenticated the same way `api_sync_automation` already is (`X-API-Key`
> against `User.api_key`), and a small helper that calls Telegram's
> `sendMessage` Bot API using `TELEGRAM_BOT_TOKEN` from `.env`. Ask me for the
> bot token and the target `chat_id` if they're not already in `.env`. Apply
> the same local-SQLite ALTER TABLE approach already used elsewhere in this
> project for adding a column without a migration framework. Test end-to-end
> with a real `curl` call before calling it done.

## Phase 2 — A skill that wires an automation repo up to reporting its own failures

Run from inside an automation's own repo (not this dashboard's), same
calling convention as `automation-portfolio-sync`.

- Decide the skill's name and scope first — this is a genuinely separate
  concern from `automation-portfolio-sync` (runtime failure alerting vs.
  static `dashboard/*.md` doc sync), so it's likely worth being its own new
  skill rather than a bolted-on step. Open question, not decided yet.
- The skill drops a small, reusable script into the automation's repo (e.g.
  `scripts/report_failure.py`) that `POST`s to phase 1's endpoint using the
  automation's own `api_key` (the same key already used for the existing
  push-sync story) and an error message.
- It also has to explain — not silently guess — where to wire the call in:
  wrap the automation's actual entrypoint in `try`/`except`, call the
  script's function from the `except` block. A skill can't safely infer an
  arbitrary codebase's real entrypoint, same limitation
  `automation-portfolio-sync` already has for source docs it won't invent —
  this stays a guided, manual step per automation.

### Prompt to kick this off
> Design and write a new Claude Code skill (name TBD — not
> `automation-portfolio-sync`, this is a different concern: runtime failure
> alerting, not doc sync) that, run from inside an automation's repo, drops in
> a small script reporting failures to this dashboard's
> `POST /api/automations/<slug>/report-failure` endpoint (see
> `docs/telegram_alerts_plan.md` phase 1 for the exact contract once phase 1
> is done), and walks the user through wiring it into their automation's real
> entrypoint. Follow this project's own skill-authoring conventions (see
> `~/.claude/skills/automation-portfolio-sync/SKILL.md` for the shape a
> sibling skill in this same problem space already takes).

## Phase 3 — Surface failures in the dashboard's own UI

- Show `last_failure_at`/`last_failure_message` on the automation detail page
  (`src/templates/automation_detail.html`), near the existing "Статус"/останній
  коміт panels in `.detail-side` — same sidebar the ROI and "Плани" panels
  already live in.

### Prompt to kick this off
> Implement phase 3 of `docs/telegram_alerts_plan.md`: add a small panel to
> `src/templates/automation_detail.html`'s `.detail-side` column showing
> `automation.last_failure_at`/`last_failure_message` when present, styled
> consistently with the existing status/commit panels there.

## Open questions

- Shared alerts channel vs. per-owner `chat_id` (phase 1) — deferred to
  "start with shared, revisit later," not a hard decision yet.
- The phase 2 skill's actual name and whether it stays fully separate from
  `automation-portfolio-sync` or ends up sharing some reference files with it.
- Alert *conditions* beyond "an uncaught exception happened" (`OBSERVABILITY.md`'s
  `## Alerts` already flags thresholds/trigger conditions as undecided) —
  out of scope for this push-model MVP, revisit once real automations are
  actually wired up.
