# data/

- `raw/` — the untouched input. Never edited or overwritten in place.
- `interim/` — transformed but not yet final.
- `processed/` — what the dashboard/pipeline actually reads.
- `external/` — third-party data pulled in as-is.

All four are typically gitignored (large and/or binary) — these folders (with a
`.gitkeep` each) exist so the convention is visible even though the data itself isn't
committed. If a subfolder isn't needed for this project, delete it rather than leaving
it as unexplained dead weight.
