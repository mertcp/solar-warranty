"""Synthetic portfolio. No real plant SCADA."""

import random
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
REGIONS = ("Skåne", "Jutland", "Eifel", "Alentejo", "Sud", "Nord")
INVERTER_MODELS = ("InvMax-500", "SolDrive-630", "GridFeed-480")
# Worst site stays SV-03 for the demo story; numbers are intentionally irregular.
WORST_SITE = 3
WORST_PROFILE = (0.8087, 67.34, 71.82)
OTHER_HOT = {
    7: (0.8612, 57.91, 77.46),
    11: (0.8833, 51.77, 61.88),
}


def _reset() -> None:
    create_tables()
    Base.metadata.drop_all(ENGINE)
    create_tables()


def _add_daily(session, site, string_id, metric, start, end, rng, wobble=0.0):
    for day in range(DAYS):
        progress = day / max(DAYS - 1, 1)
        value = start + (end - start) * progress
        if wobble:
            value *= 1.0 + rng.uniform(-wobble, wobble)
        session.add(
            Reading(
                site=site,
                string_id=string_id,
                recorded_on=TODAY - timedelta(days=DAYS - 1 - day),
                metric=metric,
                value=round(value, 2),
            )
        )


def seed(session: Session, rng=None) -> dict:
    if rng is None:
        rng = random.Random(20261104)
    site_count = 14
    counts = {"sites": 0, "strings": 0}
    for number in range(1, site_count + 1):
        code = "SV-{0:02d}".format(number)
        if number == WORST_SITE:
            scale, module_end, inverter_end = WORST_PROFILE
        elif number in OTHER_HOT:
            scale, module_end, inverter_end = OTHER_HOT[number]
        else:
            scale = rng.uniform(0.928, 0.991)
            module_end = rng.uniform(44.2, 49.8)
            inverter_end = rng.uniform(49.6, 58.3)

        rated = round(rng.uniform(2187.0, 3864.0), 1)
        yield_factor = rng.uniform(0.00408, 0.00492)
        guaranteed = round(rng.uniform(0.885, 0.905), 3)

        site = Site(
            code=code,
            name=rng.choice(
                ("{0} Field", "{0} Array", "{0} Park", "Upper {0}", "{0} West")
            ).format(code),
            region=rng.choice(REGIONS),
            rated_kwp=rated,
            guaranteed_pr=guaranteed,
            warranty_start=date(rng.randint(2019, 2022), rng.randint(1, 12), rng.randint(1, 26)),
            inverter_model=rng.choice(INVERTER_MODELS),
            inverter_serial="SN{0}{1}".format(rng.randint(100000, 999999), rng.choice("ABCDEFGHJKLMNPQR")),
        )
        session.add(site)
        counts["sites"] += 1

        strings = []
        for label in ("B1", "B2", "B3", "B4"):
            if label == "B4":
                mod = module_end
            else:
                mod = round(rng.uniform(43.5, 48.9), 1)
            unit = StringUnit(site=site, label=label, module_temp_c=mod)
            session.add(unit)
            strings.append(unit)
            counts["strings"] += 1
        session.flush()
        for unit in strings:
            if unit.label == "B4":
                start_m = round(rng.uniform(42.8, 45.6), 1)
                _add_daily(session, site, unit.id, "module_temp_c", start_m, module_end, rng, 0.018)

        expected_daily = rated * yield_factor
        actual_daily = expected_daily * scale
        _add_daily(session, site, None, "expected_kwh", expected_daily, expected_daily, rng, 0.012)
        _add_daily(
            session,
            site,
            None,
            "daily_kwh",
            actual_daily * rng.uniform(0.965, 0.995),
            actual_daily,
            rng,
            0.022,
        )
        inv_start = round(rng.uniform(47.2, 52.8), 1)
        _add_daily(session, site, None, "inverter_heatsink_temp_c", inv_start, inverter_end, rng, 0.015)

        planned = TODAY - timedelta(days=rng.randint(11, 19))
        if number == WORST_SITE:
            actual = None
        else:
            actual = planned - timedelta(days=rng.randint(1, 4))

        session.add(
            Milestone(
                site=site,
                kind=rng.choice(
                    ("warranty inspection", "annual O&M visit", "commissioning check")
                ),
                planned_on=planned,
                actual_on=actual,
            )
        )

        if number == WORST_SITE:
            session.add(
                Event(
                    site=site,
                    occurred_at=datetime(2026, 10, 28, 14, 17, 33),
                    summary="Inverter derated on overtemperature. String B4 module temp elevated.",
                    fault_code="E{0}".format(rng.randint(37, 48)),
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
