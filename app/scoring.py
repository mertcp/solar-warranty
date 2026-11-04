"""Turn seeded measurements into PR, kWh gap, thermal stress, and SLA lateness."""

MODULE_NORMAL_C = 45.0
MODULE_LIMIT_C = 75.0
INVERTER_NORMAL_C = 50.0
INVERTER_LIMIT_C = 85.0


def performance_ratio(actual_kwh, expected_kwh):
    if expected_kwh <= 0:
        return 1.0
    return round(min(actual_kwh / expected_kwh, 1.2), 3)


def kwh_gap_vs_guarantee(actual_kwh, expected_kwh, guaranteed_pr):
    """kWh short of the warranty floor over the window."""
    floor = expected_kwh * guaranteed_pr
    return round(max(floor - actual_kwh, 0.0), 1)


def thermal_stress(module_temp_c, inverter_heatsink_c):
    module_span = max(MODULE_LIMIT_C - MODULE_NORMAL_C, 1.0)
    inverter_span = max(INVERTER_LIMIT_C - INVERTER_NORMAL_C, 1.0)
    m = max(0.0, min((module_temp_c - MODULE_NORMAL_C) / module_span, 1.5))
    i = max(0.0, min((inverter_heatsink_c - INVERTER_NORMAL_C) / inverter_span, 1.5))
    return round(max(m, i) * 100.0, 1)


def sla_days_late(planned_on, actual_on, today):
    done = actual_on or today
    if done <= planned_on:
        return 0
    return (done - planned_on).days


def site_state(performance_ratio, guaranteed_pr, thermal_stress, sla_days_late):
    if performance_ratio < guaranteed_pr - 0.02 or sla_days_late > 7:
        return "claim_ready"
    if performance_ratio < guaranteed_pr or thermal_stress > 55:
        return "underperforming"
    return "healthy"
