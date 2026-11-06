"""Portfolio API. Claim draft uses one model call over scored site data."""

from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.claim import draft
from app.db import create_tables, get_session
from app.models import ClaimDraft, Milestone, Reading, Site, StringUnit
from app.scoring import (
    kwh_gap_vs_guarantee,
    performance_ratio,
    site_state,
    sla_days_late,
    thermal_stress,
)
from app.seed import seed

app = FastAPI(title="Warranty Pulse", version="0.1.0")
APP_DIR = Path(__file__).resolve().parent


def session_scope():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@app.on_event("startup")
def startup():
    create_tables()
    session = get_session()
    try:
        if session.query(Site).count() == 0:
            seed(session)
    finally:
        session.close()


def _site_row(site: Site) -> dict:
    return {
        "id": site.id,
        "code": site.code,
        "name": site.name,
        "region": site.region,
        "rated_kwp": site.rated_kwp,
        "guaranteed_pr": site.guaranteed_pr,
        "performance_ratio": site.performance_ratio,
        "kwh_gap": site.kwh_gap,
        "thermal_stress": site.thermal_stress,
        "sla_days_late": site.sla_days_late,
        "state": site.state,
        "formula_pr": "PR = actual kWh ÷ expected kWh",
        "formula_gap": "kWh gap = max(0, expected × guaranteed PR − actual)",
    }


def _one(session: Session, site_id: int) -> Site:
    site = (
        session.query(Site)
        .options(
            joinedload(Site.strings),
            joinedload(Site.readings),
            joinedload(Site.milestones),
            joinedload(Site.events),
            joinedload(Site.claim_drafts),
        )
        .filter(Site.id == site_id)
        .first()
    )
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


def _recompute(site: Site, today: date) -> None:
    by_day_actual = {}
    by_day_expected = {}
    inverter_temp = 50.0
    module_temp = 45.0
    for reading in site.readings:
        if reading.metric == "daily_kwh":
            by_day_actual[reading.recorded_on] = reading.value
        elif reading.metric == "expected_kwh":
            by_day_expected[reading.recorded_on] = reading.value
        elif reading.metric == "inverter_heatsink_temp_c":
            inverter_temp = reading.value
        elif reading.metric == "module_temp_c":
            module_temp = max(module_temp, reading.value)
    actual_sum = sum(by_day_actual.values())
    expected_sum = sum(by_day_expected.values())
    site.performance_ratio = performance_ratio(actual_sum, expected_sum)
    site.kwh_gap = kwh_gap_vs_guarantee(actual_sum, expected_sum, site.guaranteed_pr)
    site.thermal_stress = thermal_stress(module_temp, inverter_temp)
    late = 0
    for milestone in site.milestones:
        late = max(late, sla_days_late(milestone.planned_on, milestone.actual_on, today))
    site.sla_days_late = late
    site.state = site_state(
        site.performance_ratio, site.guaranteed_pr, site.thermal_stress, site.sla_days_late
    )
    for unit in site.strings:
        if unit.label == "B4":
            unit.module_temp_c = module_temp


class ReadingIn(BaseModel):
    metric: str
    value: float
    string_label: Optional[str] = None
    recorded_on: Optional[date] = None


class MilestoneIn(BaseModel):
    kind: str
    planned_on: date
    actual_on: Optional[date] = None


class DecisionIn(BaseModel):
    status: str
    edited_action: Optional[str] = None


@app.get("/")
def home():
    return FileResponse(APP_DIR / "portfolio.html")


@app.get("/assets/solar-farm.jpg")
def solar_farm_background():
    return FileResponse(APP_DIR / "assets" / "solar-farm.jpg", media_type="image/jpeg")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/portfolio")
def portfolio(session: Session = Depends(session_scope)):
    sites = session.query(Site).all()
    rows = [_site_row(site) for site in sites]
    rows.sort(key=lambda row: (row["kwh_gap"], row["thermal_stress"]), reverse=True)
    return rows


@app.get("/sites/{site_id}")
def site_detail(site_id: int, session: Session = Depends(session_scope)):
    site = _one(session, site_id)
    body = _site_row(site)
    body["inverter_model"] = site.inverter_model
    body["inverter_serial"] = site.inverter_serial
    body["warranty_start"] = site.warranty_start.isoformat()
    body["strings"] = [
        {"id": unit.id, "label": unit.label, "module_temp_c": unit.module_temp_c}
        for unit in site.strings
    ]
    body["readings"] = [
        {
            "on": reading.recorded_on.isoformat(),
            "metric": reading.metric,
            "value": reading.value,
            "string_label": reading.string_unit.label if reading.string_unit else None,
        }
        for reading in sorted(site.readings, key=lambda item: (item.recorded_on, item.metric))
    ]
    body["milestones"] = [
        {
            "kind": item.kind,
            "planned_on": item.planned_on.isoformat(),
            "actual_on": item.actual_on.isoformat() if item.actual_on else None,
        }
        for item in site.milestones
    ]
    body["events"] = [
        {
            "at": event.occurred_at.isoformat(),
            "summary": event.summary,
            "fault_code": event.fault_code,
        }
        for event in sorted(site.events, key=lambda item: item.occurred_at)
    ]
    body["claim_drafts"] = [
        {
            "id": item.id,
            "action": item.edited_action or item.action,
            "window": item.window,
            "kwh_at_risk": item.kwh_at_risk,
            "confidence": item.confidence,
            "status": item.status,
        }
        for item in site.claim_drafts
    ]
    return body


@app.get("/sites/{site_id}/evidence")
def evidence(site_id: int, session: Session = Depends(session_scope)):
    """JSON bundle a warranty desk would attach to a claim."""
    site = _one(session, site_id)
    draft = site.claim_drafts[-1] if site.claim_drafts else None
    return {
        "site": site.code,
        "rated_kwp": site.rated_kwp,
        "inverter_serial": site.inverter_serial,
        "warranty_start": site.warranty_start.isoformat(),
        "guaranteed_pr": site.guaranteed_pr,
        "performance_ratio": site.performance_ratio,
        "kwh_gap": site.kwh_gap,
        "thermal_stress": site.thermal_stress,
        "sla_days_late": site.sla_days_late,
        "formulas": {
            "pr": "actual_kwh / expected_kwh",
            "gap": "max(0, expected_kwh * guaranteed_pr - actual_kwh)",
        },
        "milestones": [
            {
                "kind": m.kind,
                "planned_on": m.planned_on.isoformat(),
                "actual_on": m.actual_on.isoformat() if m.actual_on else None,
            }
            for m in site.milestones
        ],
        "events": [
            {"at": e.occurred_at.isoformat(), "summary": e.summary, "fault_code": e.fault_code}
            for e in site.events
        ],
        "claim_draft": None
        if draft is None
        else {
            "action": draft.edited_action or draft.action,
            "window": draft.window,
            "kwh_at_risk": draft.kwh_at_risk,
            "status": draft.status,
        },
    }


@app.post("/sites/{site_id}/readings")
def add_reading(site_id: int, incoming: ReadingIn, session: Session = Depends(session_scope)):
    site = _one(session, site_id)
    string_id = None
    if incoming.string_label:
        match = next((unit for unit in site.strings if unit.label == incoming.string_label), None)
        if match is None:
            raise HTTPException(status_code=400, detail="Unknown string label")
        string_id = match.id
    when = incoming.recorded_on or date.today()
    session.add(
        Reading(
            site=site,
            string_id=string_id,
            recorded_on=when,
            metric=incoming.metric,
            value=incoming.value,
        )
    )
    session.flush()
    _recompute(site, date.today())
    session.commit()
    return _site_row(site)


@app.post("/sites/{site_id}/milestones")
def add_milestone(site_id: int, incoming: MilestoneIn, session: Session = Depends(session_scope)):
    site = _one(session, site_id)
    session.add(
        Milestone(
            site=site,
            kind=incoming.kind,
            planned_on=incoming.planned_on,
            actual_on=incoming.actual_on,
        )
    )
    session.flush()
    _recompute(site, date.today())
    session.commit()
    return _site_row(site)


@app.post("/sites/{site_id}/claim")
def claim_draft(site_id: int, session: Session = Depends(session_scope)):
    site = _one(session, site_id)
    action, window, kwh, confidence = draft(site)
    record = ClaimDraft(
        site=site,
        created_at=datetime.now(),
        action=action,
        window=window,
        kwh_at_risk=kwh,
        confidence=confidence,
        status="draft",
    )
    session.add(record)
    session.commit()
    return {
        "id": record.id,
        "action": record.action,
        "window": record.window,
        "kwh_at_risk": record.kwh_at_risk,
        "confidence": record.confidence,
        "status": record.status,
    }


@app.post("/claims/{claim_id}/decision")
def decide(claim_id: int, incoming: DecisionIn, session: Session = Depends(session_scope)):
    if incoming.status not in ("accepted", "edited", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be accepted, edited, or rejected")
    record = session.get(ClaimDraft, claim_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Claim draft not found")
    record.status = incoming.status
    if incoming.status == "edited":
        if not incoming.edited_action:
            raise HTTPException(status_code=400, detail="An edited action is required")
        record.edited_action = incoming.edited_action
    session.commit()
    return {
        "id": record.id,
        "action": record.edited_action or record.action,
        "window": record.window,
        "kwh_at_risk": record.kwh_at_risk,
        "status": record.status,
    }
