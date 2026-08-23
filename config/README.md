# config/

Environment-specific settings — schedules, thresholds, feature flags, endpoints that
differ between dev/staging/prod.

Never a secret here, even a low-stakes one. Secrets go in `.env.example` (names only)
plus whatever Phase 5 decided — this folder is for values that are fine to see in a diff.
