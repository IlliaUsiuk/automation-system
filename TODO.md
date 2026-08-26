# TODO

- [x] "What's happening right now" on the automation card — shipped as a plain fact,
  not a guessed stage: the dashboard shows the repo's last commit message + when it
  happened (a commit's wording doesn't reliably map to lifecycle phase, so it isn't
  interpreted into a narrative). `dashboard/SUMMARY.md`'s optional `## Current Stage`
  overrides it for anything a commit can't say ("очікуємо погодження", "заблоковано").
  Sits next to `Status`, doesn't replace it.
- [ ] This still only updates on a manual "Оновити з GitHub" click, not actually live —
  a webhook or scheduled poll would close that gap, not attempted yet.
