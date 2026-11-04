# Solar warranty performance demo

Living plan for this repo. Created 4 Nov 2026. Status: local demo at http://127.0.0.1:8001/ — portfolio, array view, claim draft. Deploy only when Mert asks.

In a new chat in this folder, say: read `PROJECT.md` and continue from the next unchecked step.

## What we are building

A demo SaaS for **commercial or utility-scale solar**: live **heat** (module and inverter temperature), **on-time** service and commissioning milestones, and **performance** (expected vs actual energy) in one place so an operator can **support a warranty claim** with evidence, not spreadsheets.

Interview line: a **performance and warranty twin** for a site — not a CAD layout or a physics PV simulator. The product ranks sites and strings by underperformance and thermal stress, shows the warranty curve vs measured output, and drafts a claim packet a human can accept or edit.

Pitch: catch hot strings and missed SLA windows before they become disputed warranty cases; when output stays below guarantee, export a traceable claim summary.

Audience: CV demo for cloud / SaaS solutions pre-sales (same lane as TraceRail). Synthetic sites and weather only. No real customer names, SCADA exports, or OEM confidential curves.

## Why this shape

| Signal on the CV | What the demo shows |
|---|---|
| Cloud / SaaS | Hosted site dashboard, health check, CI |
| API | Inverter telemetry ingest, milestone events, OpenAPI |
| AI automation | Draft warranty claim summary from measured gaps |
| Data science | Performance ratio, thermal index, on-time score |
| Pre-sales | Short script a recruiter can click through |

Done means a public GitHub repo and optionally a live URL. Finish on the Mac first; deploy only when Mert asks.

## Locked decisions (draft — confirm in chat)

- **Domain:** solar O&M and warranty — customer metric is **lost kWh** and **claim readiness** (documented gap vs guarantee).
- **Workflow:** ingest telemetry → score heat + performance + on-time → rank sites → AI draft claim narrative → human accept or edit → export summary (PDF or JSON stub is enough for demo).
- **Screens:** fleet of sites, site detail (heatmap or string table), warranty chart (guaranteed vs actual), claim draft panel.
- **Twin depth:** site → block/inverter → string; badges for thermal stress, performance gap, SLA miss; one “if we wait” line (e.g. kWh at risk or days until warranty window closes).
- **World:** synthetic portfolio, ~10–20 sites, mixed climates; seed 2–3 obvious underperformers and one thermally stressed string.
- **Inputs (minimum honest set — two signals per theme):**
  - **Heat:** module temperature (°C), inverter heatsink temperature (°C).
  - **Performance:** AC power (kW) or daily energy (kWh) vs **expected** from simple model (rated capacity × irradiance proxy × temperature derate).
  - **On-time:** planned vs actual dates for commissioning, preventive visit, or warranty inspection (stored as events, not sent by the inverter as “on time”).
- **Scoring:** visible formulas on the page (e.g. performance ratio, thermal stress index, SLA days late).
- **Stack (match TraceRail discipline):** FastAPI, simple UI, SQLite or Postgres, one JSON LLM call for claim draft, optional similarity (“sites with same inverter model and gap pattern”).
- **Data:** synthetic only.
- **Repo:** `solar-warranty` on GitHub (`mertcp`), separate from TraceRail.

## Data to collect for warranty-related failures

Output warranties need proof of **underperformance after weather normalization**, not raw low kWh. Product and workmanship claims need **fault history**, **identity**, and **timelines**. Below: what real operators collect, then what this demo will actually implement.

### Performance and availability (kWh guarantee)

| Signal | Role in a claim |
|--------|------------------|
| AC power or daily energy (inverter or revenue meter) | Actual vs guaranteed curve |
| Irradiance proxy (POA or GHI) + ambient temperature | Expected energy; performance ratio (PR) |
| Plant availability vs grid outage / curtailment flags | Separates equipment loss from grid or export limit |

### Thermal and electrical stress (defect / accelerated wear)

| Signal | Role in a claim |
|--------|------------------|
| Module temperature (°C) | Hot strings, mounting issues, soiling interaction |
| Inverter heatsink / internal temperature (°C) | Derating, fan or filter failure |
| String voltage and current | Mismatch, open circuit, partial failure |
| Isolation or leakage trend (when monitored) | Moisture ingress, safety-related OEM cases |

### Fault trail and equipment identity (RMA, batch, recall)

| Signal | Role in a claim |
|--------|------------------|
| Inverter fault / alarm codes with timestamps | Maps to OEM defect categories |
| Monitoring offline vs zero production | Data gap is not underperformance |
| Module and inverter serial numbers, model, firmware | Warranty start, batch recalls, known bugs |
| Commissioning / energization date | Warranty clock and notice windows |

### Site context (defend or exclude)

| Signal | Role in a claim |
|--------|------------------|
| Soiling or cleaning events | Owner O&M vs manufacturer |
| Shading or obstruction changes | External cause |
| Grid voltage / frequency excursions | Inverter disconnect or derate — often excluded |

### Process and on-time (workmanship + contract)

| Signal | Role in a claim |
|--------|------------------|
| Planned vs actual inspection, repair, OEM ticket opened | SLA and procedural disputes |
| Date underperformance threshold crossed + owner notification | Many contracts require notice within X days |
| Work order or photo attachments (optional in demo) | Evidence pack |

### Implemented in v1 demo (smallest honest set)

| Theme | Stored signals | Notes |
|-------|----------------|-------|
| Heat | `module_temp_c`, `inverter_heatsink_temp_c` | Rank thermal stress index |
| Performance | `daily_kwh`, `expected_kwh` (from rated kWp × seeded irradiance × simple temp derate) | PR and kWh gap vs warranty line |
| On-time | Milestone records (planned vs actual date) | Not inferred from inverter |
| Faults | Synthetic `events` (e.g. overtemperature derate, string fuse open) | Feeds claim draft |
| Identity | Site metadata: inverter model, warranty start, guaranteed PR | One spotlight site below guarantee |

### Documented but out of v1 code

String-level IV, drone thermography, live paid weather APIs, full CMMS, legal PDF generation, GIS/shading physics.

Interview line: *We normalize with weather, split grid/curtailment from equipment loss, tie alarms and heat to serial and dates, and timestamp OEM notification — that is the minimum defensible warranty file.*

## Out of scope

- Full GIS, single-line diagrams, shading simulation, MPPT physics
- Real weather API keys as default (seed irradiance series locally; optional live weather only if Mert approves cost)
- Blockchain, billing, full legal document generation
- Real utility or EPC data from work

## Build order

- [x] Name the product and repo (**Solar warranty demo** / `solar-warranty`, GitHub `mertcp`)
- [x] Schema: site, string, readings, milestones, events, claim_drafts (`app/models.py`)
- [x] Seed 14 sites (fixed RNG), 30-day wobbly series, spotlights SV-03, SV-07, SV-11 (`app/seed.py`)
- [x] Scoring: PR, kWh gap, thermal stress, SLA days (`app/scoring.py`)
- [x] API: portfolio, site detail, POST reading/milestone, claim draft (`app/api.py`)
- [x] UI: portfolio table, array side view, claim accept/edit (`app/portfolio.html`)
- [x] README, curl, demo script; CI on push (`check.yml`)
- [ ] Deploy only when Mert asks (state cost and get approval)

## Eight-minute script (target)

1. One site is below warranty curve for two weeks; module temp is high on one string.
2. Fleet view ranks by kWh gap and thermal stress.
3. Open the site: see heat trend, performance ratio, missed inspection date.
4. Draft claim: “String B4 — sustained PR 0.82 vs 0.90 guarantee; inverter heatsink elevated; request OEM review under year-5 output warranty.”
5. Accept or edit; show what would be attached (readings summary, dates, formula).
6. `/docs` — how a monitoring portal POSTs the next 15-minute reading.

## Risks

- Scope creep into real PV simulation — keep expected energy a simple transparent formula.
- Looks like a dashboard with no warranty story — always show guarantee line + claim draft.
- Duplicating TraceRail too closely — lead with **kWh and warranty**, not delay minutes.

## How the code should read

Mert will walk a recruiter through this repo. The code should read like a system engineer wrote a short demo, not like a generated framework.

- Keep files small and the path straight. A function should be readable aloud.
- Use plant words: site, string, kWh gap, performance ratio, warranty inspection.
- Comment the PR / gap formula and any decision the name does not show. Do not comment every function.
- Skip extra layers, base classes, banners, and placeholder scaffolds.
- After each step, Mert should be able to explain the changed file in a few sentences.

## Before the project is finished

Warn Mert first. Do not delete these notes until he agrees.

Then remove everything that exists for the agent rather than for a recruiter:

- This section, "How the code should read," and "How we work in Cursor."
- `.cursor/rules/solar-warranty.mdc` and any other agent instructions, except the cost-approval rule.
- Comments, commands, and files whose only job is to steer the agent or to hide that an agent wrote the code.

Keep the product, the README, the demo script, and the PR / gap explanation. The plain coding style stays. The notes about that style do not.

## Cost approval

Finish the code on this Mac. Do not deploy to the cloud until Mert says the demo is ready for recruiters.

Any action that can cost Mert money must stop first. State the amount, then ask exactly: **“This will cost you this amount. Do you approve this action?”** Do not continue until he says yes. This includes Fly.io, Azure, OpenAI, paid weather APIs, and any other paid service. **Keep this rule when agent-only notes are removed.**

Do not call OpenAI, start a cloud host, or buy a weather API without that sentence and a yes.

## How we work in Cursor

- This folder is the project. Open it before coding (not the TraceRail folder).
- This file is the memory. Update it when a decision changes.
- `.cursor/rules/solar-warranty.mdc` keeps a new chat inside this scope.
- Resume line: read `PROJECT.md` and continue from the next unchecked step.
- Prefer minimum token use: small diffs, read only files needed for the task, no deploy loops unless Mert asks.
- Commit and push when Mert asks or when a finished step is done.

## Open decisions for Mert

1. **Product name** on the CV (e.g. SunTrace, WattGuard, keep generic “Solar warranty demo”).
2. **Asset tree:** site → inverter → string, or site → combiner → string?
3. **Warranty type in the demo:** output (kWh) guarantee only, or also product/workmanship (simpler to start with **output** only).
4. ~~**Same GitHub account**~~ — yes, `mertcp` / public `solar-warranty`.
