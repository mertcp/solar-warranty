# Solar warranty demo

Synthetic portfolio monitoring for **heat**, **on-time milestones**, and **performance vs warranty** — so an operator can support a claim with evidence.

Runs on this Mac first. All data is synthetic.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.api:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/ — site **SV-03** should lead the portfolio. Click a string on the array sketch; the claim line appears without a separate button.

## Measurements (v1)

| Theme | Metrics |
|-------|---------|
| Performance | `daily_kwh`, `expected_kwh` → PR and kWh gap vs guaranteed PR |
| Heat | `module_temp_c` (string B4), `inverter_heatsink_temp_c` |
| On-time | Milestone planned vs actual dates |
| Faults | Event log with optional fault code |

## API (recruiter curl)

```bash
curl -s http://127.0.0.1:8001/portfolio | python3 -m json.tool | head -30
curl -s http://127.0.0.1:8001/sites/3 | python3 -m json.tool | head -40
curl -s -X POST http://127.0.0.1:8001/sites/3/claim
curl -s http://127.0.0.1:8001/sites/3/evidence | python3 -m json.tool | head -25
```

Open `/docs` for ingest (`POST /sites/{id}/readings`, `POST /sites/{id}/milestones`).

## Architecture

```
telemetry → FastAPI + SQLite → PR, gap, thermal, SLA → claim draft (LLM if OPENAI_API_KEY)
```

Without `OPENAI_API_KEY`, claim text uses the same scored numbers via rules in `app/claim.py`.

## Demo script (8 min)

1. SV-03 is below the 0.90 PR guarantee; string B4 runs hot.
2. Portfolio ranks by kWh gap and shows missed warranty inspection.
3. Click the array; read the OEM review draft.
4. Accept or edit; formulas stay visible.
5. `/docs` — monitoring portal posts the next daily reading.

Separate from [TraceRail](https://github.com/mertcp/tracerail).
