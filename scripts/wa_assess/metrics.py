"""Derive delivery, incident and credential figures from the synthetic exports.

Findings quote these figures through placeholders such as ``{delivery.rollbacks}``, so the prose in the report
cannot drift from the exports.
"""

from __future__ import annotations

import csv
import re
import statistics
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

KEY_AGE_LIMIT_DAYS = 90
PLACEHOLDER = re.compile(r"\{([a-z_]+)\.([a-z0-9_]+)\}")


def round_half_up(value: float, places: int = 1) -> float | int:
    """Round the way people do on paper (2.25 -> 2.3), not banker's rounding. Zero places returns an int."""
    quantum = Decimal(1).scaleb(-places)
    rounded = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)
    return int(rounded) if places == 0 else float(rounded)


ALLOWED = {
    "outcome": {"success", "rolled_back", "failed"},
    "detected_by": {"customer", "alarm", "staff"},
    "postmortem": {"yes", "no"},
    "console_access": {"true", "false"},
    "mfa_active": {"true", "false"},
    "access_key_active": {"true", "false"},
}


def _rows(path: Path) -> list[dict[str, str]]:
    """Read an export and reject values the counts below would silently misread."""
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"{path.name}: no rows")
    for number, row in enumerate(rows, start=2):
        for column, allowed in ALLOWED.items():
            if column in row and row[column] not in allowed:
                raise ValueError(
                    f"{path.name}:{number}: {column} is {row[column]!r}, expected one of {sorted(allowed)}"
                )
    return rows


def delivery(path: Path, window_days: int) -> dict:
    rows = _rows(path)
    total = len(rows)
    rollbacks = sum(row["outcome"] == "rolled_back" for row in rows)
    failed = sum(row["outcome"] == "failed" for row in rows)
    return {
        "deployments": total,
        "deploys_per_week": round_half_up(total / (window_days / 7)),
        "rollbacks": rollbacks,
        "failed": failed,
        "change_failure_rate_pct": round_half_up(100 * (rollbacks + failed) / total),
        "median_lead_time_hours": round_half_up(statistics.median(float(row["lead_time_hours"]) for row in rows)),
    }


def incidents(path: Path) -> dict:
    rows = _rows(path)
    restore = [int(row["minutes_to_restore"]) for row in rows]
    longest = max(rows, key=lambda row: int(row["minutes_to_restore"]))
    return {
        "total": len(rows),
        "customer_detected": sum(row["detected_by"] == "customer" for row in rows),
        "postmortems": sum(row["postmortem"] == "yes" for row in rows),
        "median_minutes_to_detect": round_half_up(statistics.median(int(row["minutes_to_detect"]) for row in rows), 0),
        "median_minutes_to_restore": round_half_up(statistics.median(restore), 0),
        "longest_minutes_to_restore": max(restore),
        "longest_incident": longest["incident_id"],
    }


def access_keys(path: Path) -> dict:
    rows = _rows(path)
    active_ages = [int(row["access_key_age_days"]) for row in rows if row["access_key_active"] == "true"]
    return {
        "active_keys": len(active_ages),
        "active_over_90_days": sum(age > KEY_AGE_LIMIT_DAYS for age in active_ages),
        "oldest_age_days": max(active_ages, default=0),
        "console_users_without_mfa": sum(
            row["console_access"] == "true" and row["mfa_active"] == "false" for row in rows
        ),
    }


def compute(repo_root: Path, window_days: int) -> dict:
    exports = repo_root / "data" / "synthetic" / "exports"
    return {
        "delivery": delivery(exports / "deployments.csv", window_days),
        "incidents": incidents(exports / "incidents.csv"),
        "access_keys": access_keys(exports / "credential-report.csv"),
    }


def fill(text: str, figures: dict) -> str:
    """Replace every ``{group.name}`` placeholder. An unknown placeholder raises KeyError."""

    def value(match: re.Match[str]) -> str:
        group, name = match.groups()
        if group not in figures or name not in figures[group]:
            raise KeyError(f"unknown placeholder {match.group(0)}")
        return str(figures[group][name])

    return PLACEHOLDER.sub(value, text)
