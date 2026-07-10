# Roadmap — Phases 1 & 2 (locked 2026-07-11, post-STORM review)

This roadmap supersedes the draft Phase 1/2 plans. It was stress-tested by a
STORM-engine research pass (18 grounded research + verification agents,
2026-07-10/11): three survey lanes (exemplar structure, currency, genre
judgment) and six assessor personas (energy modeler, water expert, India
researcher, grid analyst, civil-society user, replicator). Every load-bearing
claim was adversarially re-verified against primary sources. Full evidence:
the STORM knowledge-brain dashboard (see README link) and
`data/manifest.json` watchlist.

**The one-sentence verdict:** the foundation held (LBNL calibration anchors
exact; VA-#1 independently replicated by Bloomberg's identical method; the
open-India-dataset niche still open), but the plan needed four blocking fixes
and a reframe of its flagship finding from *water-stress verdict* to
*exposure screen + consumptive-growth + peak-day story*.

---

## Phase 1.0 — Blocking fixes (do before any Phase 1 code)

**1.0.1 Licensing restructure.** The repo is mislicensed: root MIT covers
data derived from the ODbL IM3 atlas (share-alike). Fix: MIT for code only;
`LICENSE-DATA` (ODbL 1.0) for the IM3-derived facility database; move
FracTracker-derived columns (mw_capacity etc.) to a separately-flagged file
under FracTracker's terms (non-commercial, cited) or regenerate-by-script;
per-source license column in the manifest. Email FracTracker for written
permission to (a) redistribute matched fields, (b) archive dated snapshots on
Zenodo (mission-aligned; approval plausible). ODbL cannot absorb NC content
(ODI compatibility guide) — without permission, the merged table is never
publishable under one license.

**1.0.2 Citability infrastructure.** Zenodo–GitHub integration (concept DOI +
per-release DOIs, PUDL-style calendar versions e.g. v2026.07); CITATION.cff;
conda-lock lockfile (geopandas/GDAL is where pip pinning fails); GitHub
Actions CI: pytest on join/match logic, pandera schemas on published layers,
headline-number regression tests, license/manifest consistency check.

**1.0.3 FracTracker re-pull.** The pinned snapshot is stale: the April 7,
2026 rebuilt tracker holds 1,400+ facilities (803 in pre-development/
construction vs our "723 proposed") and NEW fields: cooling method, MW,
power sourcing, NDAs, backup generators, co-located generation. Re-pull, pin
date, re-run the ≤500 m match, and **re-measure the "~95% cooling tech
unknown" assumption** — it drives the width of every water band. Use
Suspended/Cancelled statuses as empirical realization-rate data.

**1.0.4 Virginia reframe (communication fix, applies immediately).** The
finding survives — Bloomberg (May 2025) used the same Aqueduct BWS≥40 method
and also ranked Virginia #1 — but reframe from "VA is the #1 water-stressed
state" to: *VA has the most facilities sited in a highly-utilized supply
basin (Occoquan, BWS 0.60), where data centers are the region's
fastest-growing consumptive user (ICPRB: 1% of withdrawals but 9% of annual
consumptive use, ~4→22 MGD avg and ~15→80+ MGD peak-day by 2050) and
peak-day demand is the binding constraint.* Quote JLARC's "currently
sustainable" preemptively; caveat that Aqueduct cannot see UOSA's ~30-40 MGD
reuse augmentation (up to 90% of reservoir inflow in droughts) or CO-OP
drought storage; note basin-of-location ≠ basin-of-supply (203 Loudoun
facilities score Low next door on the same regional system). Spot-check the
Henrico basin (731905) against local sources before publishing county ranks.

**1.0.5 Archive fragile upstreams now.** Download Cambium 2024 LRMER
workbooks into the manifest immediately: NREL was renamed National Laboratory
of the Rockies (Dec 1, 2025), URLs are migrating, future vintages uncertain.
Watchlist: official eGRID2024 (6+ months overdue), Cambium 2025, Uptime 2026,
EIA pilot-survey results (post-Sept 2026), NY moratorium signature, MeitY
NDCP finalization, FERC RTO show-cause filings (due Aug 17, 2026).

---

## Phase 1 — US: consumption, three-signal carbon, two-channel water (4–5 wks)

**1.1 Energy model — hierarchical, scenario-first.** Sample facility
class/vintage first, then *correlated* (density, PUE, load factor) draws —
independent draws artificially narrow tails. Priors: Guidi et al.
(arXiv 2411.09786) ~91.75 W/sqft on gross footprints (OSM/IM3 areas are
gross; vendor 200-400 W/sqft figures are white-space — a factor-of-2 trap);
utilization scenarios u ∈ {0.48, 0.58, 0.663, 0.70} (Guidi 2026); load factor
defined on nameplate IT capacity, wide (~0.4–0.75), citing Norris's load
factor / capacity-utilization / uptime distinction. PUE: energy-weighted
national anchor 1.45 (2024)→1.36 (2030), AI-serving 1.145 — never center
hyperscale classes on Uptime's respondent-weighted 1.54. Calibration to LBNL
2025 Update (192 TWh 2024; 649 TWh 2030 ref; bounds 521–843) is
**model-to-model anchoring, labeled as such** — LBNL is shipments-based (no
sqft anywhere, so not circular), report uncalibrated + calibrated totals and
the implied adjustment factor; propagate calibration-target uncertainty
(LBNL's own historicals moved ~10% between vintages; peers span 177–250 TWh
incl. NBER ~250). Present scenario bands + named sensitivity axes (adopt
LBNL's published parameters), not "probabilities". Seeds/config in
version-controlled YAML; MC error + seed-sensitivity in QA.

**1.2 Carbon — three signals + a fourth for futures.**
- Attributional: eGRID2023 (official, pinned) + Cornerstone community
  eGRID2024 (Zenodo 18968658, built with EPA's own code, avg −3%) as labeled
  sensitivity.
- Consequential/siting: Cambium 2024 LRMER (county-FIPS→GEA join via workbook
  mapping tabs; levelized over explicit facility lifetime; Mid + higher-fossil
  scenario; **OBBBA vintage caveat** — pre-July-2025 policy assumptions
  understate future fossil margins).
- Hourly/attribution-geography: EIA-930 hourly BA CO2 (per-BA xlsx, not API)
  or Open Grid Emissions 2024 (Zenodo) for top-20 clusters — delivers the
  24/7-CFE stretch with zero new methodology. Add **attribution geography as
  a first-class sensitivity axis**: Guidi et al. 2026's BA-level method gives
  ~545 gCO2/kWh fleet intensity vs our ~357 (786 lb/MWh) subregion-weighted —
  geography alone moves intensity ~50%.
- Futures/BTM: ~90 GW (59 projects, >25% of announced pipeline) is
  behind-the-meter gas (Cleanview) — grid-mix signals don't apply; add an
  onsite-generation EF channel and cross-reference FracTracker×Cleanview.
- PPAs: location-based primary, market-based gap as a sidebar (documented
  ~662% divergence), never adjust facility numbers with unverifiable claims;
  note GHG Protocol Scope 2 revision (final ~2027) converging on this design.

**1.3 Water — two channels, recalibrated, peak-day promoted to CORE.**
- On-site WUE scenario bands *(central | low | design)*: hyperscale 0.55 /
  colo 0.65 (Ren 2026 fleet 2024) | 0.27–0.37 (Microsoft FY25 fleet; LBNL
  2023 implied) | 1.5–1.9 evaporative design-conditional. ~75% consumptive
  fraction; summer ≈ 3× annual (ICPRB); peaking factors 3–10.
- Off-site EWIF: Siddik et al. 2024 WRR / LBNL Water IMPACT factors (hourly,
  BA-level, withdrawal AND consumption) — and ALWAYS hydro-inclusive
  (~3.15 gal/kWh) vs hydro-exclusive (~0.47) bands + PPA caveat: the
  ITIF/Potter critique script is known in advance; encode it.
- Scarcity: summer BWS (already computed) first-class alongside annual +
  Aqueduct 2030/2050; USGS NWAA HUC12 Supply-Use Index as US cross-check.
- **Basin-of-supply overlay (new):** join facilities to community-water-system
  service areas (EPA/ORD or SimpleLab/EPIC) → PWS → source basin; report
  location-basin AND supply-basin stress (dissolves the Loudoun/PW artifact).
- **Peak-day vs local system capacity — now a headline deliverable** (the
  Tucson/Dalles/Howell hearing format): reframed as open facility-cluster
  downscaling + cross-validation of Han/Li/Wierman/Ren "Small Bottle, Big
  Pipe" (their national envelope 697–1,451 MGD/2030 becomes a validation
  target; they released no code/data). Capacity from state Drinking Water
  Viewer portals (VA DWV has design capacity; **federal SDWIS does not**) +
  EPA 2006 CWSS surplus priors + ICPRB numbers for the WMA.

**1.4 Futures — stage-conditional, not scalar.** Map FracTracker statuses to
EPRI's stage framework (Low 90/25/0 – Mid 100/75/10 – High 100/100/30 % for
UC/advanced/early); stratify by sponsor type (balance-sheet hyperscaler vs
speculative developer — uniform queue rates are a category error); evidence:
ERCOT Apr 2026 (410.6 GW queue, 71.5% no-studies, 5.8 GW energized), Georgia
PSC (~65% of announced load removed), PUCT $50k/MW rule as speculation cull
(pre/post regime sensitivity); regulatory-exposure discount from the
moratorium wave (63 local actions; NY ≥20 MW pause pending). Benchmark
against the IM3+EPRI BA-level load dataset (OSTI 10.57931/3007669) and
explicitly improve its population-weighted flat-8760 allocation.

**1.5 Dual-risk 2.0 — retire the binary.** The 284 count compounds two
thresholded model outputs; replace with a sensitivity surface over
(CO2 threshold × attribution geography × water indicator × utilization),
with screening language: "screened for elevated basin stress — local
validation required" (WRI's own July 2025 guidance; the Great-Lakes
false-positive class documented in QA).

**1.6 Validation + external review.** Anchors: LBNL Water IMPACT Tool
(BA factors), EPRI state dashboard (VA 39–57% of state electricity by 2030),
NBER ~250 TWh upper bound, JLARC's utility-metered VA water (2.1B gal 2023)
as the water-side calibration, Siddik 2021 patterns, Han et al. envelope.
Location-accuracy audit: sample-verify IM3/OSM coordinates vs permit sources;
request Business Insider's permit-based database via academic access.
**Documented external review round (3–5 named reviewers) before publication**
— every credible exemplar has one.

**1.7 Decision-surface outputs (new).** (a) Per-county one-page PDFs: 3–5
local comparative numbers, plain language, WCAG 2.1 AA (ADA Title II deadline
Apr 2027 for ≥50k jurisdictions) — the hearing artifact; the dashboard is the
research layer. (b) Correction infrastructure BEFORE publication: per-datum
provenance field, PEC-style evidence hierarchy, submission form, BHRRC-style
operator right-of-reply with responses published verbatim. (c) Misuse FAQ
("what these numbers are / are not"; per-query framings; both aggregation
scales side-by-side). (d) Disclosure block (author, no funding, corrections
log). (e) Utility service-territory / PUC-jurisdiction layer (Project Blue
shows county vetoes get bypassed at the PUC).

---

## Phase 2 — India: open dataset + groundwater overlay + EC audit (5–7 wks)

**Differentiation (rewritten):** CEEW (Feb 2026), WRI India (May 2026, closed
DataCenterMap inputs), and S&P (Sept 2025) already own the headline "half of
India's DCs are in water-stressed regions." What remains unclaimed, and what
Phase 2 delivers: **(1) the first openly licensed, analysis-ready,
provenance-documented India facility dataset; (2) the facility ×
CGWB-block-groundwater overlay with Aqueduct 2030/2050 projections, expressed
in INGRES regulatory categories with a CGWA-notified-area flag (162 areas
where new groundwater abstraction is already legally regulated — the
permit-relevant instrument); (3) a Parivesh environmental-clearance
transparency audit.** Framed as an empirical test of the industry perception
CEEW documented ("water risk low to medium") — expect pushback; provenance
bar set accordingly.

**2.1 Open dataset — primary sources, not Baxtel.** Baxtel's ToS prohibits
scraping/derivative works (research-citation carve-out only; the one
published precedent kept its dataset closed). Compile GEM-style from primary
sources: Parivesh EC records, state SEIAA orders, operator press releases,
trade press, OSM/satellite verification (Guidi's validation step) — with a
per-facility source-URL provenance column. Baxtel/DataCenterMap: discovery
and cross-check only, cited, never republished. License CC BY 4.0 (GODL-2013
government inputs are clean) → eligible for a *Scientific Data* data paper.
Reconcile counts (CEEW ~271, DataCenterMap 296, ATLAS 342) in the QA report.
**Release the dataset FIRST (Zenodo DOI + preprint) to timestamp the claim —
the niche is closing on a months timescale.**

**2.2 Groundwater overlay.** Vintage: Dynamic GWRA **2025** (6,762 units,
730 over-exploited — the 2024 figures are stale). Mechanics: INGRES has no
GIS export; join INGRES tabular categorization to open block/tehsil
boundaries (LGD/SoI via india-geodata, DataMeet, CoRE Stack) with a
documented name-match QA table (blocks/taluks/mandals/firkas don't map 1:1 —
budget 1–2 extra weeks). India-WRIS WMS as visual cross-check only.

**2.3 Carbon — assemble and cite, don't construct.** CEA V21 national
(0.7117 tCO2/MWh FY2024-25) + Ember SET 2026 state intensities + consumption-
based caveat (ACS EST flow-tracing precedent). The plan's own finding stands:
India's story is water and land, not grid mix. Redirect the saved 1–2 weeks
to 2.2 and 2.5.

**2.4 Metro clusters — updated anchors.** Knight Frank (June 2026): 1.6 GW
live / 8.3+ GW pipeline; Mumbai 766.6 MW (47%), Chennai 191.5 MW (~12%),
NCR 174.5 MW (now #3, ahead of Hyderabad 151.4), Kolkata 23.1; AI = 78% of
2025 leasing. CEEW aggregates (~0.5% electricity, ~150 BL water 2024 —
itself Mordor-sourced, treat as prior not measurement) as top-down
calibration mirroring LBNL's Phase 1 role. India-adjusted priors: hot-climate
PUE >1.7; 100 MW evaporative ≈ 2 ML/day.

**2.5 Pipeline scenarios.** Vizag 6.5 GW state target (Google/AdaniConneX
$15B campus; district groundwater lowest in AP at 2.12 TMC; AP's
seawater-cooling policy provision as mitigation variable); Jamnagar as
1 GW proposed / 3 GW ambition scenario band (June 2026 reporting revised the
3 GW); Knight Frank 8.3 GW pipeline, phantom-discounted with Phase 1.4's
stage-conditional machinery.

**2.6 Policy overlay — expanded.** 15 state policies; Rajasthan 2025 (water
conditions) + AP (seawater cooling) + draft National DC Policy (20-yr tax
exemptions conditioned on PUE; four DC Economic Zones; MeitY consultations
revived June 2026 — may finalize mid-project) + Budget 2026-27 tax holiday to
2047 + Tamil Nadu lapsed (Mar 31, 2026, recalibration pending). The killer
chart stays: where incentives point vs where the water is, now with the
Rajasthan-conditioning counterfactual AND the NDCP-PUE scenario.

**2.7 EC transparency audit (new, high-leverage).** Parivesh DC clearances
coded for operational-water disclosure, approval latency (Google Tarluvada:
10 days, no public hearing), hearing status. Converts Parivesh's weakness as
a data source into the most newsworthy finding; directly services CEEW's
mandatory-disclosure recommendation.

**2.8 Engagement + funding.** WRI India: pitch the open-data upgrade of
their closed-data viz (concrete co-publication). CEEW: EC-audit + overlay as
evidence for their disclosure agenda. Digital Futures Lab: SME reviewer.
Green Screen Coalition Catalyst Fund (funded DFL; grants to $50k): apply with
the open dataset as the deliverable. India-specific user research (who is the
"county planner" equivalent — state industrial-development officers, SEIAA
members) scoped before the review round.

---

## Sequencing — as amended by the red-team pass (binding)

**Honest timeline at 15–20 hrs/wk solo: ~6–8 months end-to-end** (Phase 1.0
≈ 2–3 wks; Phase 1 ≈ 10–14 wks; Phase 2 ≈ 9–13 wks). The earlier 10–13-week
figure priced each workstream at a week; 1.3 alone contains three
mini-projects. Plan to this reality, not the optimistic one.

**Priority ruling:** under the real hours constraint, the **India dataset
v0.1 wins any tiebreak** — the niche closes on a months timescale while the
US field is already occupied by LBNL/Bloomberg/Business Insider. v0.1 =
top-6 metros, operational facilities, full per-facility provenance, Zenodo
DOI — shipped in the first 2–3 weeks of Phase 2, pulled EARLIER if
niche-closure risk sharpens. Tiering is stated in the data paper; timestamp
beats completeness.

**Serialize, don't parallelize:** one person context-switching between US
hydrology and Parivesh scraping finishes neither. One hard handoff date from
Phase 1 core to Phase 2.

**Week-1 external asks (calendar latency runs in parallel or not at all):**
FracTracker permission email, reviewer recruitment (3–5 names), WRI
India/CEEW/DFL introductions, Business Insider database request, Green Screen
fund inquiry — all sent in week 1 with a send date and a no-reply fallback
each. FracTracker Plan B (if denied): FracTracker columns become
regenerate-by-script only (documented script, no redistribution), and the
open US release ships without them.

**Working rules:** (1) every task gets a definition-of-done and a time-box at
phase start; if the box expires, ship without it and log the cut. (2)
Vintages pin at phase start; watchlist events get a logged note, not a
re-run, until after publication. (3) No new dataset enters the manifest
without a license/ToS row first. (4) Every headline: one central estimate,
one band, top two named sensitivities — no sensitivity sprawl. (5) Sample
error rates in audits; never chase individual facilities.

**Positioning decision (made):** neutral open-data provider leads;
findings are framed as disclosure-gap measurement in service of the
incumbents' own recommendations (CEEW's mandatory-disclosure agenda).
Right-of-reply extends to Indian operators; the EC audit is shared with
WRI India/CEEW BEFORE publication, and engagement precedes the audit's
release, not the reverse.

**Scoop contingency:** a mid-Phase-1 working-paper/preprint checkpoint stakes
the US peak-day claim (in case Han et al. release code/data);
**hiring-manager checkpoint (October 2026):** a portfolio layer — README with
three findings, one dashboard view, one short method note, 10-minute entry
point — ships regardless of research completeness.

**Deferred to v2 (cuts are scoping, not omission — stated in the README):**
hourly EIA-930 analysis beyond one demo cluster; full BTM-gas channel (one
documented EF sensitivity note instead); national basin-of-supply coverage
(VA/WMA + top-5 clusters in v1); national peak-day downscaling (Occoquan +
2–3 confirmed-coverage clusters in v1; Han et al. as comparison table);
dual-risk surface beyond two axes (attribution geography × water indicator);
county PDFs beyond 3–5 (one user-tested first — three user interviews before
PDF design); full right-of-reply program (corrections log + GitHub issue
template in v1); PUC-jurisdiction layer; pandera/full test pyramid (headline
regression tests + license check in v1); full 15-state India policy coding
(killer chart + one table in v1); 2.4/2.5 collapse into one scenario memo.

Every stage still lands with an updated qa_report.md and manifest entries.

## Phase 3 — Communication & dissemination (STORM-tested 2026-07-12)

**3.0 Immediate track (independent of Phases 1–2 — the hearing window is
open NOW).** Ship a minimum-viable one-pager from Phase 0 data (county
facility count, basin status with screening language, dual-risk flag, one
fiscal-context line) for 1–2 counties with named active processes (candidates:
Frederick County MD staff report due Sept 2026; Fort Wayne IN task force
Sept 8), submitted as written public comment AND handed to the local resident
group. Target 6–8 weeks. The moratorium wave (Prince George's, Greenwood,
DeKalb, Hill Co, NC) peaks now; artifacts deferred to Q1 2027 miss it.

**3.1 Metric-design armor (labels and FAQs are necessary, not sufficient —
the bottle-of-water statistic's caveats did not survive press extraction).**
Hard rules: no per-query / per-prompt / household-equivalent numbers anywhere,
ever; headline numbers only at facility/county/water-system scale; ranges
printed on the chart face (crop-proof); three pre-written quotable statistics
with exact phrasing and a "how to cite this number" line; a two-front FAQ
("if you think this is alarmist" / "if you think water risk is debunked",
citing Ren's own correction); a one-page reconciliation of our 34.7% vs
Business Insider's widely-cited 40% (different universes: 1,240 permitted vs
1,474 OSM-derived facilities) — the single most predictable challenge.

**3.2 Launch kits + adoption plumbing.** Every headline release (US peak-day;
India dataset v0.1; EC audit) ships as a kit: one-page press note led by ONE
quotable stat with uncertainty inside the sentence; GEM-style dated-release
citation string ("India DC Facility Dataset, v0.1, [month] 2026 release");
3–5 CC-BY chart PNGs sized for republication; OWID-style per-chart embed
codes + archived/versioned chart URLs + data downloads with attribution text
inside the files; the FracTracker/GPPD disclaimer stack on every artifact
("modeled estimates, not measured values; may differ from operator-reported
figures; corrections with evidence welcome").

**3.3 Intermediary strategy (nobody's dashboard walks into a hearing by
itself).** One named carrier org per target geography (PEC-style org or
resident coalition per US county; SEIAA-adjacent researchers/DFL for India);
one-pagers designed as remix material (editable text, copy-this-table
blocks, explicit CC-BY remix invitation); curator-channel asks (PEC library,
state equivalents) sent early, week-1-style. Adoption is counted via
derivative artifacts (county staff memos, association briefs, law-firm
alerts, UPSC-aggregator pages).

**3.4 India comms.** English-first stands for SEIAA/industrial-officer/
think-tank audiences (the EC process works in English). Add only: two
targeted local-language one-page summaries (Telugu for Vizag, Marathi for
Mumbai) late in Phase 3, one Hindi key-stats page formatted for the
UPSC-aggregator ecosystem, and a Mongabay-India-first press pitch (it chains
into Scroll and the Hindi ecosystem). No blanket translation.

**3.5 Press protocol — a gated milestone, not a parallel deliverable.**
Prerequisites: disclaimers live, corrections/errata page live, right-of-reply
completed (solicit named companies' comment on headline claims and print
responses), and an explicit go/no-go at the October checkpoint. Mechanics:
single-outlet exclusive (~1-week lead) to one data-savvy beat reporter; the
ONE India press moment is the dataset release (preprint-stage coverage
cannibalizes journal-stage; data papers rarely earn standalone press).
Register with SciLine now. Journalist contact is human-only.

**3.6 Publication track (mechanics corrected).** Zenodo v0.1 DOI + preprint
FIRST (unchanged). Preprint default: SSRN or SocArXiv (arXiv now requires a
personal endorsement for first-time submitters — if wanted, add an
endorsement ask to the week-1 batch; OSF Preprints is suspended). Scientific
Data submission only after dataset v1.0: $2,690 APC (waiver request AT
submission), ~11-day first-decision signal, 162-day median to acceptance —
a spring-2027 credential, NOT an October artifact. Data in Brief only as a
conditional fallback (secondary-data exception must be argued). **Binding
AI-policy items:** Methods-section disclosure of LLM/agent use (Springer
Nature policy), no AI-generated imagery, and a citation-verification gate
(every DOI/URL resolved) on all agent-drafted prose — release-blocking.

## Phase 4 — Validation, engagement, stewardship (STORM-tested 2026-07-12)

**4.1 External review** as locked (named reviewers, recruited week 1) — now
explicitly including review of agent-written analytical code.

**4.2 Partnerships, re-scoped to how the institutions actually work.**
WRI India ladder: (i) open-data upgrade/swap for their closed-data viz
(contact: the named expert on their May 2026 piece), (ii) co-authored
technical note or blog, (iii) formal co-publication only if WRI initiates
(their 4-internal + 4-external reviewer process is a multi-month lift). CEEW:
data-provider/cited-source + reviewer role (their collaboration mode is
org-to-org). Licensing firewall: the CC-BY dataset releases independently and
FIRST; a co-branded report may be closed-licensed without contaminating it.

**4.3 Funding.** Green Screen Catalyst Fund's 2026 cycle is CLOSED
(nominations ended Mar 15; grants started July). Convert to: monitor for
~Feb 2027 nominations (individuals eligible), keep a 1-page concept note
ready, and run an alternative-funder scan — the plan currently has zero live
2026 funding paths.

**4.4 Stewardship (SLA framing replaced by field norms).** No published
response-time SLA (no comparable org has one; an unkeepable promise creates
risk). Instead: evidence-required intake ("dispute this record" link per
facility, GEM-style — page URL + open-source reference required), public
CHANGELOG.md + errata page, DOI-versioned releases (the Climate TRACE
incident shows a public changelog is the decisive rebuttal asset). Internal
best-effort targets only (acknowledge ~14d, adjudicate ~30d). Write the
freeze/sunset playbook NOW as a repo artifact: pre-drafted freeze banner,
"data as of [date]" on every table/chart, per-release Zenodo archive,
COVID-Tracking-Project-style sunset note template. Evidence: early explicit
freezing is respected; silent staleness is what damages. Maintenance budget:
~0–2 issues/month absent press + one 1-hour weekly triage block; the real
event-driven load is press/records/legal correspondence, covered by a
pre-written response kit.

**4.5 Legal & incident posture.** Disclosed methodology is the legal shield
for modeled estimates (ONY v. Cornerstone). Documented pushback pattern is
reverse-records/trade-secret suits and rhetorical methodology disputes — and
in India, cease-and-desist + parallel civil/criminal defamation (BNS 356)
with ex parte injunctions and court-ordered platform blocking that has
already reached GitHub and Vercel (Delhi HC, June 2026 — our exact stack).
India rules: facility records described strictly in government-source
language, no accusatory characterizations anywhere (including commit
messages), EC audit framed as transparency measurement, every India release
mirrored to Zenodo. Escalations (human-only, always): any legal-flavored
letter, correction demand from a company or counsel, records denial citing
trade secrets, press inquiry, or anything from an Indian court/lawyer.
Pre-publication risk read from a university media-law clinic (free;
FracTracker used Harvard's Cyberlaw Clinic). Harris affiliation is never
presented as institutional backing (it confers no liability protection).

## Delegated execution model (Opus/Sonnet build · Fable advises)

The build is executed by Claude Opus 4.8 and Sonnet 5 agents under root
**CLAUDE.md** (Claude Code does not read AGENTS.md natively). Governing
findings: prose rules are advisory and degrade in long sessions — hard rules
are enforced by CI + hooks in agent-unwritable paths; agents saturate visible
tests while failing held-out ones (gap larger for smaller models), so
verification is held-out golden tests + fresh-context adversarial review;
long analytical sessions collapse (~47pp late-turn degradation), so every
task is single-session with one materialized artifact and a runnable
pass/fail definition-of-done written before execution.

- **Enforcement before delegation:** CI (1.0.2) is the first gating
  deliverable — headline-number regression tests marked never-edit,
  test-integrity check (fails PRs that delete/weaken tests), license/manifest
  consistency (any file under data/ without a manifest license row fails),
  citation-verification, and a per-query-equivalence lint on comms artifacts.
- **Routing:** Sonnet 5 solo = scaffolding, re-pulls, archival, dashboard
  plumbing, templates, WCAG checks (intro pricing ends Aug 31, 2026 — the
  cheap window). Opus 4.8 + PR review = joins, refactors, stage-mapping code.
  Human/Fable-gated, never delegated = every prior/parameter/scenario choice,
  calibration methodology, anything reaching a headline number or public
  sentence, licensing decisions, all external communications and
  publication actions.
- **Fable usage is approval-gated** and reserved for phase-boundary plan
  revisions, parameter sign-off sessions, red-teams, and STORM syntheses.
- **Review contract:** ~6–8 true review hrs/wk caps throughput at ~8–12
  small PRs/wk; transcript-level review (not diff-only) for anything touching
  tests, statistics, the manifest, or headline numbers; agent self-report of
  completion is never accepted — definition-of-done is an externally runnable
  command.
- **Realistic few-weeks scope:** 1.0.2 + 1.0.3 + 1.0.5 complete; 1.1–1.4 as
  config-driven skeletons with TODO-gated parameters awaiting sign-off;
  Phase 3.0 one-pager; launch-kit templates. Delegation does NOT compress the
  6–8 month timeline (METR: felt speedup is unreliable); track merged
  definitions-of-done per week and re-plan at week 3.

## Success criteria (de facto, per PDIA)

1. An energy-systems and a water-resources reviewer each sign off (documented
   review round) without a "this conflates X with Y" finding.
2. The India dataset earns a DOI, a data-paper submission, and at least one
   external citation or reuse (WRI India/CEEW engagement counts).
3. By Nov 15, 2026: one Phase-0-derived one-pager submitted into at least
   one county public record (written comment or staff-report citation), with
   the docket link logged — carried by an identified intermediary; derivative
   artifacts (staff memos, association briefs) count as adoption. Fall-2026
   metrics are citation/reuse-shaped, not policy outcomes (the JLARC clock:
   even the gold-standard study took two sessions to yield disclosure bills).
4. Every headline number carries a range, a method label, and survives the
   pre-written red-team scripts (ITIF/Potter/Masley class attacks).
