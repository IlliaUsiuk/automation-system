# 1. Stack and architecture for the Automation ROI Dashboard

## Status
Accepted

## Context
The project needs a stack chosen from nothing (no existing code). It's an internal
Supplax tool: a dashboard listing company automations and their ROI, expected to grow
to medium scale, with planned external (beyond-corporate-network) login access and
integrations with GitHub, ClickUp, and Telegram.

## Decision
We will build the dashboard as a Node/TypeScript Next.js monolith, storing the
automation registry and ROI metrics in Postgres, rather than splitting into separate
services or picking a different language/framework.

## Consequences
Easier: one deployable unit to run and reason about; Next.js's built-in API routes
cover both the UI and the data-access layer without a separate backend service;
Postgres gives relational structure for automations/skills/owners/ROI records and
their relationships. Harder: if the project later needs to scale a specific piece
(e.g. a heavy token-tracking ingestion path) independently of the UI, splitting it out
of the monolith will be a deliberate follow-up decision, not free.
