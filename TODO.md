# TODO

- [ ] Real-time build stage on the automation card — the current `Status` enum
  (idea / in_development / ready_not_launched / live / archived) is too coarse to
  show what's actually happening right now while someone is building it. Need a
  finer, live-updating "current stage" (e.g. writing code / testing / review /
  deploying) that updates without a full GitHub re-sync. Open questions before
  building: where does this signal come from (an agent pushing status updates? a
  richer summary/SUMMARY.md field re-read on a timer? a webhook?), and does it
  replace `Status` or sit alongside it as a more granular sub-field.
