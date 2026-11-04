"""Synthetic portfolio. No real plant SCADA."""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db import ENGINE, create_tables
from app.models import Base, Event, Milestone, Reading, Site, StringUnit
from app.scoring import (
    kwh_gap_vs_guarantee,
    performance_ratio,
    site_state,
    sla_days_late,
    thermal_stress,
)

TODAY = date(2026, 11, 3)
DAYS = 30
GUARANTEED_PR = 0.90
# (site_number, kwh_scale, module_temp, inverter_temp) — scale < 1 underperforms
SPOTLIGHTS = {
    3: (0.82, 68.0, 72.0),
    7: (0.86, 58.0, 78.0),
    11: (0.88, 52.0, 62.0),
}


def _reset() -> None:
    create_tables()
    Base.metadata.drop_all(ENGINE)
    create_tables()


def _add_daily(session, site, string_id, metric, start, end):
    for day in range(DAYS):
        progress = day / max(DAYS - 1, 1)
        value = start + (end - start) * progress
        session.add(
            Reading(
                site=site,
                string_id=string_id,
                recorded_on=TODAY - timedelta(days=DAYS - 1 - day),
                metric=metric,
                value=round(value, 2),
            )
        )


def seed(session: Session) -> dict:
    counts = {"sites": 0, "strings": 0}
    for number in range(1, 13):
        code = "SV-{0:02d}".format(number)
        spotlight = SPOTLIGHTS.get(number)
        scale = spotlight[0] if spotlight else 0.97 + (number % 4) * 0.005
        module_end = spotlight[1] if spotlight else 46.0 + (number % 3)
        inverter_end = spotlight[2] if spotlight else 52.0 + (number % 2)

        site = Site(
            code=code,
            name="{0} Solar Park".format(code),
            region=("Nord" if number % 2 else "South"),
            rated_kwp=2500.0 + number * 120,
            guaranteed_pr=GUARANTEED_PR,
            warranty_start=date(2021, 6, 1),
            inverter_model="InvMax-500",
            inverter_serial="IM-{0:05d}".format(10000 + number),
        )
        session.add(site)
        counts["sites"] += 1

        strings = []
        for label in ("B1", "B2", "B3", "B4"):
            unit = StringUnit(site=site, label=label, module_temp_c=module_end if label == "B4" else 47.0)
            session.add(unit)
            strings.append(unit)
            counts["strings"] += 1
        session.flush()
        for unit in strings:
            if unit.label == "B4":
                _add_daily(session, site, unit.id, "module_temp_c", 45.0, module_end)

        expected_daily = site.rated_kwp * 0.0045
        actual_daily = expected_daily * scale
        _add_daily(session, site, None, "expected_kwh", expected_daily, expected_daily)
        _add_daily(session, site, None, "daily_kwh", actual_daily * 0.98, actual_daily)
        _add_daily(session, site, None, "inverter_heatsink_temp_c", 50.0, inverter_end)

        planned = TODAY - timedelta(days=14)
        actual = None if number == 3 else TODAY - timedelta(days=16)
        session.add(
            Milestone(
                site=site,
                kind="warranty inspection",
                planned_on=planned,
                actual_on=actual,
            )
        )

        if number == 3:
            session.add(
                Event(
                    site=site,
                    occurred_at=datetime(2026, 10, 28, 14, 20),
                    summary="Inverter derated on overtemperature. String B4 module temp elevated.",
                    fault_code="E042",
                )
            )

        session.flush()
        actual_sum = actual_daily * DAYS
        expected_sum = expected_daily * DAYS
        pr = performance_ratio(actual_sum, expected_sum)
        gap = kwh_gap_vs_guarantee(actual_sum, expected_sum, site.guaranteed_pr)
        heat = thermal_stress(module_end, inverter_end)
        late = sla_days_late(planned, actual, TODAY)
        site.performance_ratio = pr
        site.kwh_gap = gap
        site.thermal_stress = heat
        site.sla_days_late = late
        site.state = site_state(pr, site.guaranteed_pr, heat, late)

    session.commit()
    return counts


def main() -> None:
    _reset()
    session = __import__("app.db", fromlist=["get_session"]).get_session()
    try:
        counts = seed(session)
    finally:
        session.close()
    print("sites={0} strings={1}".format(counts["sites"], counts["strings"]))


if __name__ == "__main__":
    main()
