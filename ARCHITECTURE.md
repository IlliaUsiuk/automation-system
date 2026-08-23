# Architecture

## Overview
A Next.js (TypeScript) monolith backed by Postgres. It renders a registry of the
company's automations and their ROI, and will grow into the place employees log in to
see automation status, ownership, and (later) live alerts and token-spend tracking.
Detailed page/API structure is intentionally not fixed yet — pending the design pass
that follows this Stage 0 bootstrap.

## Components
- **Web app (Next.js)** — pages/UI for the registry and ROI views, plus a login-gated
  area for external/internal access (see `SECURITY.md`).
- **API routes (Next.js)** — reads/writes the automation registry and ROI records in
  Postgres; will also serve as the entry point for GitHub/ClickUp metadata lookups.
- **Postgres database** — automations (including a free-text description),
  skills catalog, categories, ownership, ROI metrics, links to GitHub/ClickUp, and
  relationships between automations (related/dependent automations — see
  `ROADMAP.md`'s "Now" scope) — this last one implies a self-referencing link between
  automation records, not just flat rows.
- *(Next/Later)* Telegram notifier for automation failures; token-usage tracker.

## Data Flow
An automation is registered (manually at first, later via a self-service skill that
pushes metadata through GitHub) → its metadata and ROI figures are stored in Postgres
→ the dashboard reads that data and renders the registry + ROI cards for whoever is
logged in.

## Key Decisions
- ADR-0001 — Next.js + Postgres + monolith for v1. See `docs/adr/0001-stack-and-architecture.md`.

## Scale & Constraints
Expected scale: medium — built to handle company-wide usage and a growing automation
count, not just a handful of records, but no high-traffic/high-availability design
work is warranted yet.
