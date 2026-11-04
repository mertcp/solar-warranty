"""One JSON model call drafts a warranty claim from site measurements.

Without OPENAI_API_KEY the same numbers drive a rule draft.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

WINDOWS = ("within 30 days", "before next OEM review", "after notice period")


def brief(site):
    strings = [{"label": unit.label, "module_temp_c": unit.module_temp_c} for unit in site.strings]
    milestones = [
        {
            "kind": item.kind,
            "planned_on": item.planned_on.isoformat(),
            "actual_on": item.actual_on.isoformat() if item.actual_on else None,
        }
        for item in site.milestones
    ]
    events = [
        {
            "at": event.occurred_at.isoformat(),
            "summary": event.summary,
            "fault_code": event.fault_code,
        }
        for event in sorted(site.events, key=lambda item: item.occurred_at)[-3:]
    ]
    return {
        "site": site.code,
        "inverter_model": site.inverter_model,
        "inverter_serial": site.inverter_serial,
        "guaranteed_pr": site.guaranteed_pr,
        "performance_ratio": site.performance_ratio,
        "kwh_gap": site.kwh_gap,
        "thermal_stress": site.thermal_stress,
        "sla_days_late": site.sla_days_late,
        "strings": strings,
        "milestones": milestones,
        "recent_events": events,
    }


def draft_from_rules(site):
    gap = site.kwh_gap
    hot = max(site.strings, key=lambda unit: unit.module_temp_c)
    if site.state == "claim_ready":
        return (
            "Request OEM review for {0}: sustained PR {1} vs {2} guarantee; "
            "string {3} module temp {4}°C; {5:g} kWh below warranty floor.".format(
                site.code,
                site.performance_ratio,
                site.guaranteed_pr,
                hot.label,
                hot.module_temp_c,
                gap,
            ),
            "within 30 days",
            gap,
            0.82,
        )
    if site.state == "underperforming":
        return (
            "Monitor {0} and schedule warranty inspection. PR {1}, thermal stress {2}.".format(
                site.code, site.performance_ratio, site.thermal_stress
            ),
            "before next OEM review",
            gap,
            0.6,
        )
    return (
        "No warranty claim recommended for {0}. PR {1} meets guarantee.".format(
            site.code, site.performance_ratio
        ),
        "after notice period",
        0.0,
        0.5,
    )


def _parse(payload):
    action = str(payload.get("action", "")).strip()
    window = str(payload.get("window", "")).strip()
    if window not in WINDOWS:
        window = "before next OEM review"
    kwh = float(payload.get("kwh_at_risk", 0))
    confidence = float(payload.get("confidence", 0.7))
    if not action:
        raise ValueError("empty action")
    return action, window, kwh, max(0.0, min(confidence, 1.0))


def draft_from_llm(site):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    body = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You draft solar output warranty claims from monitoring data. "
                    "The inverter did not declare a claim. Use performance ratio, kWh gap, "
                    "thermal stress, milestones, and events. Reply JSON: action, window, "
                    "kwh_at_risk, confidence. action is one sentence for an asset manager."
                ),
            },
            {"role": "user", "content": json.dumps(brief(site))},
        ],
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {0}".format(api_key),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = json.loads(response.read().decode("utf-8"))
        content = raw["choices"][0]["message"]["content"]
        return _parse(json.loads(content))
    except (urllib.error.URLError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        return None


def draft(site):
    from_model = draft_from_llm(site)
    if from_model is not None:
        return from_model
    return draft_from_rules(site)
