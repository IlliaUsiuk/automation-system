# ROI — How This Is Actually Calculated

The detailed companion to `dashboard/ROI.md` — the real walkthrough behind its terse,
dashboard-parsed fields.

## Methodology
Per-automation ROI card shows time and/or money saved vs. the manual process it
replaced. The baseline comes from whatever the automation's owner records at
registration time (e.g. "this used to take 3h/week manually") — there's no independent
measurement of the pre-automation process, it's a self-reported estimate at the point
the automation gets registered. The actual capture mechanism (a field on registration,
a periodic owner check-in, or something else) is still a design-stage decision, not
settled yet. Later phases add token cost per automation (daily) as a second, ongoing
cost side of the same ROI picture — not implemented yet.

## Assumptions
- The owner's self-reported "time it used to take manually" is accurate enough to use
  as a baseline — it isn't independently verified against, say, old timesheets.
- An automation's ROI stays roughly constant once registered; nothing here re-checks
  whether the manual-process baseline is still realistic months later.

## Caveats
No real numbers exist yet for any automation — every card's ROI is currently a stated
hypothesis, not a measured result. The self-reported baseline is also a real source of
bias: an owner motivated to show their automation's value has no independent check on
the number they enter.

## Confidence — Why
Estimated, and will stay Estimated until the actual capture mechanism (which of the
options above) gets built and at least one automation reports a real post-launch
number.
