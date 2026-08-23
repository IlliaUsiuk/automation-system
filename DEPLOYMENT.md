# Deployment

## Environments
Staging + prod (bootstrap-time judgment call — see `PIPELINE.md` §7 — given external
access and medium scale are both planned; not yet explicitly confirmed by the user).

## Deploy Steps
Not decided yet — deploy target (cloud VM/container vs. serverless platform) hasn't
been chosen.

## Rollout Strategy
Direct deploy. Change history tracked via `CHANGELOG.md` + Conventional Commits, so a
rollout has a real record to roll back against.

## Rollback
Git revert + redeploy.

## Post-Deploy Verification
Automated health checks (not yet implemented — no code exists yet).
