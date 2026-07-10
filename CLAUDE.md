# Executing-agent guide — Data-Center-Sustainability-Analysis

You are an Opus 4.8 or Sonnet 5 agent executing tasks from ROADMAP.md.
Fable 5 is the approval-gated advisor; the human (Manav) reviews all PRs.
This file is advisory context; the HARD rules are enforced by CI and hooks
(see "Enforcement"). If you notice a gap between this file and the hooks,
escalate — never improvise.

## Environment (will bite you)

- Repo lives under iCloud-synced Desktop: file reads can HANG indefinitely
  when macOS evicts content. If a read/command stalls >2 min, kill it and
  report — do not retry in a loop.
- Python: ALWAYS `~/.venvs/dc_sustainability/bin/python` (never a venv inside
  the repo; never system python). No `timeout` command on this macOS.
- `main` is protected (no force-push). One task = one branch = one PR.
- Remote `upstream` is the old group repo — NEVER push to it.
- Pipeline: `code/download_data.py` → `code/preprocessing.py` →
  `code/generate_charts.py` → `code/export_web_data.py`. Full run <5 min.
  Requirements: `code/requirements.txt` (moved for Vercel). Web app: `web/`
  (Next.js, static export; `npm run dev --prefix web`).
- QA report: `data/derived-data/qa_report.md` must end "ALL CHECKS PASSED"
  after any pipeline change.

## Task protocol

1. Session start: read `PROGRESS.md` (active task, last commit, blockers,
   next action) and `git log --oneline -5`. One task per session, from
   `tasks/` (JSON entries with `blockedBy` mirroring ROADMAP order).
2. Every task has a **runnable definition-of-done** (a command, written into
   the task BEFORE execution). Your assertion of completion counts for
   nothing; only the command's output does. Hand off evidence (test output,
   commands run), not claims.
3. Single-session tasks only: one materialized artifact per task (a CSV +
   QA cell, one chart, one doc section). If a task can't finish in one
   session, it was mis-cut — stop and escalate for re-decomposition.
4. Session end: update `PROGRESS.md` (<50 lines) and log FAILED approaches
   in `CHANGELOG.md` so the next session doesn't repeat them.
5. Two consecutive failed attempts at the same subtask → stop, write up,
   escalate. Session past ~2h or ~60% context without a passing checkpoint →
   commit checkpoint, update PROGRESS.md, end session.

## Hard rules (hook/CI-enforced; violations are release-blocking)

- **Never edit tests** in the same PR as the code they test. Never delete,
  skip, or weaken assertions. Golden regression tests pin headline numbers
  (1,474 facilities; 511 / 34.7% High+; 284 dual-risk, and successors) — if
  a change moves them, that is an ESCALATION, not an edit.
- **No new data source without a manifest row first** (`data/manifest.json`:
  URL, access date, license, version_check). Files under `data/` without a
  manifest license row fail CI.
- **Never touch** LICENSE, LICENSE-DATA, or manifest license columns without
  human approval. Licensing matrix: our code MIT; IM3-derived data ODbL
  (share-alike); FracTracker fields separate/non-commercial, cited
  "Data provided by FracTracker Alliance (2026)"; Aqueduct-derived charts
  carry "Source: WRI Aqueduct, accessed [date]"; our India dataset CC BY 4.0;
  Baxtel/DataCenterMap content is NEVER republished (cited cross-check only);
  partner co-branded content may be closed — our CC-BY releases ship first
  and independently.
- **Statistics discipline:** every numeric constant, prior, or citation in
  code or prose must trace to a manifest entry or a source URL + access date
  in the same PR. You may NEVER supply a prior, parameter, or citation from
  your own knowledge — fetch-and-quote or escalate. Calibrated and
  uncalibrated results always appear as a pair. Ranges, never bare points,
  in anything public-facing.
- **Comms discipline:** no per-query / per-prompt / household-equivalent
  numbers anywhere, ever (lint-enforced). Headline stats only at
  facility/county/water-system scale, range on the chart face. India
  artifacts use government-source language only ("located in CGWA-notified
  area per [source], as of [date]"); no accusatory characterizations
  ("violating", "illegal") anywhere — including commit messages.
- **Irreversible or outward actions are human-only:** git history rewrites,
  deletions of data, Zenodo/DOI publication, releases, emails, journal or
  preprint submissions, posting anything anywhere, replying to companies,
  lawyers, or journalists.

## Escalation triggers (stop work, write up, request human/Fable review)

1. A test file and its tested code in the same change.
2. Any headline regression value changes.
3. Any new external data source/URL not in the manifest.
4. Any parameter/prior/citation you cannot trace to a listed source.
5. Anything touching LICENSE*, manifest license fields, or data
   redistribution.
6. Irreversible/outward operations (above).
7. Two consecutive failures on the same subtask.
8. Session limits hit without a passing checkpoint.
9. Any legal-flavored letter, company correction demand, press inquiry, or
   anything from an Indian court/lawyer (never reply; never alter QA'd
   numbers outside the corrections workflow).
10. Press-facing text, quotable-stat phrasing, or the misuse FAQ (drafts OK;
    shipping requires human/Fable sign-off).

## Task routing

- **Sonnet 5 solo (autonomous + logged):** scaffolding (CITATION.cff,
  conda-lock, Zenodo webhook config), FracTracker re-pull + re-match against
  existing tests, archival downloads into the manifest, web-data/dashboard
  plumbing, chart and template drafts, disclaimer/citation blocks, WCAG
  checks (axe-core), QA-report generation.
- **Opus 4.8 (PR + human review):** multi-file refactors, spatial-join and
  matching logic (Cambium county→GEA, basin-of-supply, EPRI stage mapping),
  anything with join/match semantics.
- **Human/Fable-gated (never delegated):** every prior/parameter/scenario
  choice in ROADMAP 1.1–1.3 (W/sqft, PUE anchors, WUE bands, EWIF variants,
  utilization, realization rates), calibration methodology, dual-risk surface
  design, any number or sentence that reaches a headline/dashboard/hearing
  artifact, licensing, external comms, publication mechanics.
- Dashboards are where agents over-build: dashboard scope is FROZEN at
  research/credibility layer. No new interactive decision-support features.

## Enforcement (status)

CI and hooks are themselves the first build task (ROADMAP 1.0.2) and land
via human-reviewed PR after Phase 1.0.1 merges: GitHub Actions required
checks (pytest join/match, headline regression, license/manifest consistency,
test-integrity, citation-verification, per-query lint) + PreToolUse hooks
blocking writes to `.github/workflows/`, `tests/regression/`, `LICENSE*`,
and `data/manifest.json`. Until they land, treat every hard rule above as if
enforced.

## Context docs (read on demand, not by default)

- `ROADMAP.md` — the locked plan; read the section for your task first.
- `METHODS.md` — joins, masking rules, vocabulary sync list, limitations.
- `data/manifest.json` — dataset versions, licenses, watch rules (watchlist
  events are LOGGED, not acted on, until after publication).
- `data/derived-data/qa_report.md` — current QA state.
- `web/AGENTS.md` — Next.js version notes for web work.
