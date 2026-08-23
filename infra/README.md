# infra/

One subfolder per environment (`staging/`, `prod/` — see `DEPLOYMENT.md`), not one
giant shared config — matches standard IaC practice of separating a small root
module/config from environment-specific values.

This skill doesn't know which IaC tool this project will actually use, so it doesn't
invent `.tf`/`.yaml`/etc. files here — write those for real once the tool is chosen.
This README just states the convention so the split is intentional, not accidental.
