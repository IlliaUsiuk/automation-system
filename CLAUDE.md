# CLAUDE.md

## Commit messages: Ukrainian subject line

Write commit subject lines for this repo in Ukrainian, not the usual English
convention. This automation *is* the portfolio dashboard — its own card shows
`automation.last_commit_message`, the literal last commit subject pulled live
from GitHub (`src/github_sync.py`'s `fetch_latest_commit`), directly in the
"Зараз" panel of an otherwise all-Ukrainian UI (`src/templates/
automation_detail.html`). Deliberately not translated or interpreted (see
`src/models.py`'s comment on `last_commit_message` — a raw fact, not a guessed
lifecycle stage), so an English subject there reads as broken language-mixing
on the one automation whose entry represents itself.

This is specific to this repo, not a rule for automations registered *in* the
portfolio — their repos keep normal English commit conventions; only this
one's commits are what that panel displays about itself.
