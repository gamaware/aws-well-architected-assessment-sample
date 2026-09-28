"""A second, deliberately plain implementation of the assessment rules, used only by the tests.

It shares no code with scripts/wa_assess. It reads the raw YAML and CSV files and recomputes every number the report
prints, so a bug in the scripts shows up as a disagreement instead of being copied into the expected values.
"""

from __future__ import annotations

import csv
import statistics
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import yaml

PILLAR_FILES = (
    "operational-excellence",
    "security",
    "reliability",
    "performance-efficiency",
    "cost-optimization",
    "sustainability",
    "devops",
)
CREDIT = {"met": 1.0, "partial": 0.5, "not_met": 0.0}
GAP = ("partial", "not_met")


def half_up(value: float, places: int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def load(root: Path) -> dict:
    synthetic = root / "data" / "synthetic"
    answers = {
        k: yaml.safe_load((synthetic / "answers" / f"{k}.yaml").read_text(encoding="utf-8")) for k in PILLAR_FILES
    }
    workload = yaml.safe_load((synthetic / "workload.yaml").read_text(encoding="utf-8"))
    exports = {}
    for name in ("deployments", "incidents", "credential-report"):
        with (synthetic / "exports" / f"{name}.csv").open(encoding="utf-8") as handle:
            exports[name] = list(csv.DictReader(handle))
    return {"answers": answers, "window": workload["scope"]["observation_window_days"], "exports": exports}


def percent(items: list[dict]) -> int:
    scored = [i for i in items if i["status"] in CREDIT]
    return int(half_up(100 * sum(CREDIT[i["status"]] for i in scored) / len(scored), 0))


def maturity(pct: int) -> str:
    if pct >= 80:
        return "4 Optimized"
    if pct >= 60:
        return "3 Defined"
    if pct >= 40:
        return "2 Repeatable"
    return "1 Initial"


def question_risks(pillar: dict) -> dict[str, str]:
    risks = {}
    for question in pillar["questions"]:
        gap_risks = [i["risk"] for i in pillar["items"] if i["question"] == question and i["status"] in GAP]
        risks[question] = "High" if "high" in gap_risks else "Medium" if "medium" in gap_risks else "None"
    return risks


def gaps(data: dict) -> list[dict]:
    order = {"high": 0, "medium": 1, "low": 2}
    effort = {"S": 0, "M": 1, "L": 2}
    found = []
    for position, key in enumerate(PILLAR_FILES):
        for item in data["answers"][key]["items"]:
            if item["status"] in GAP:
                found.append((order[item["risk"]], effort[item["effort"]], position, item["id"], item))
    return [entry[-1] for entry in sorted(found, key=lambda e: e[:4])]


def buckets(gap_items: list[dict]) -> dict[str, int]:
    """Base bucket from risk and effort, then each dependency takes the earliest bucket of anything needing it."""
    table = {
        "high": {"S": 30, "M": 30, "L": 60},
        "medium": {"S": 60, "M": 60, "L": 90},
        "low": {"S": 90, "M": 90, "L": 90},
    }
    plan = {i["id"]: table[i["risk"]][i["effort"]] for i in gap_items}
    dependants: dict[str, list[str]] = {}
    for item in gap_items:
        for dep in item.get("depends_on") or []:
            dependants.setdefault(dep, []).append(item["id"])

    def earliest(item_id: str, seen: frozenset = frozenset()) -> int:
        above = [earliest(d, seen | {item_id}) for d in dependants.get(item_id, []) if d not in seen]
        return min([plan[item_id], *above])

    return {item_id: earliest(item_id) for item_id in plan}


def delivery(data: dict) -> dict:
    rows = data["exports"]["deployments"]
    bad = sum(r["outcome"] in ("rolled_back", "failed") for r in rows)
    return {
        "per_week": half_up(len(rows) * 7 / data["window"], 1),
        "change_failure_rate": half_up(100 * bad / len(rows), 1),
    }


def restore_median(data: dict) -> int:
    return int(half_up(statistics.median(int(r["minutes_to_restore"]) for r in data["exports"]["incidents"]), 0))
