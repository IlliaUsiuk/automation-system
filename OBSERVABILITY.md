# Observability

## What's Instrumented
Nothing yet — no code exists. Planned: per-automation status/health signal feeding
the dashboard's registry view, and (Later, see `ROADMAP.md`) daily token-consumption
metrics per automation.

## Dashboards
None yet — this project *is* the dashboard. No separate metrics dashboard exists yet.

## Alerts
Planned (Next, see `ROADMAP.md`): Telegram alerts when an automation breaks/fails, via
a push model — see `docs/telegram_alerts_plan.md` for the phased implementation plan.
Exact trigger conditions beyond "an uncaught exception happened" are still not
decided — see that plan's "Open questions".

## Gaps
Everything — this is a bootstrap-time doc. No instrumentation, no alerting, and no
token-usage tracking exist yet.
