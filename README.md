# Warranty Pulse

**Portfolio performance and warranty claim readiness for solar operators.**

Operators lose time when underperformance shows up in spreadsheets and OEM disputes start without a clean evidence trail. This demo shows how a cloud portfolio view can rank sites by energy gap versus contract, surface heat and SLA risk on the array, and produce a claim narrative a manager can accept or edit—grounded in stored telemetry, not gut feel.

Built as a solutions pre-sales showcase: API-first, synthetic data only, runnable on a laptop. Companion project: [TraceRail](https://github.com/mertcp/tracerail) (rail condition-based maintenance).

**Repository:** [github.com/mertcp/solar-warranty](https://github.com/mertcp/solar-warranty)

---

## What you can show in five minutes

Open the dashboard, lead with site **SV-03** (below the guaranteed performance ratio). Click string **B4** on the array sketch—the OEM review line appears with PR, kWh gap, thermal stress, and inspection timing. Accept or edit the draft. Point recruiters at **/docs** for how a monitoring portal ingests the next daily reading.

Highlights worth naming aloud: ranked portfolio by business impact (kWh gap), visible warranty floor on the energy chart, human-in-the-loop claim decision, one optional LLM step when `OPENAI_API_KEY` is set (rule-based draft otherwise).

---

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.api:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/

---

## Architecture

Telemetry and milestones land in **SQLite** via **FastAPI**. Scoring computes performance ratio, kWh gap versus guarantee, thermal stress, and SLA lateness. Claim text is drafted from that evidence (`app/claim.py`)—LLM JSON when a key is present, same numbers via rules when not.

```
monitoring feed → API + database → PR, gap, heat, SLA → claim draft → accept / edit
```

---

## LinkedIn showcase copy

See **[LINKEDIN.md](LINKEDIN.md)** for a headline, short description, and highlight lines you can paste into a profile project or post.

---

## API samples

```bash
curl -s http://127.0.0.1:8001/portfolio | python3 -m json.tool | head -30
curl -s http://127.0.0.1:8001/sites/3 | python3 -m json.tool | head -40
curl -s -X POST http://127.0.0.1:8001/sites/3/claim
curl -s http://127.0.0.1:8001/sites/3/evidence | python3 -m json.tool | head -25
```

Open `/docs` for `POST /sites/{id}/readings` and milestone ingest.

---

## Disclaimer

All sites, weather, and OEM curves are **synthetic**. No real customer, SCADA export, or confidential warranty terms from any employer.
