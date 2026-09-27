"""Turn every gap into a ranked backlog item and place it on a 30/60/90-day roadmap.

Rules (docs/methodology.md and ADR 0003):

- Rank by risk (high, medium, low), then effort (S, M, L) so quick wins lead each risk band, then pillar order,
  then best-practice ID.
- A starting bucket comes from risk and effort (BASE_BUCKET).
- Work that another item depends on moves forward to that item's bucket, so nothing waits on a later bucket.
"""

from __future__ import annotations

from dataclasses import dataclass

from wa_assess.metrics import fill
from wa_assess.model import PILLARS, Assessment, Item

RISK_RANK = {"high": 0, "medium": 1, "low": 2}
EFFORT_RANK = {"S": 0, "M": 1, "L": 2}
BUCKETS = (30, 60, 90)
BASE_BUCKET = {
    ("high", "S"): 30,
    ("high", "M"): 30,
    ("high", "L"): 60,
    ("medium", "S"): 60,
    ("medium", "M"): 60,
    ("medium", "L"): 90,
    ("low", "S"): 90,
    ("low", "M"): 90,
    ("low", "L"): 90,
}


@dataclass(frozen=True)
class BacklogItem:
    rank: int
    key: str
    item: Item
    bucket: int
    base_bucket: int
    recommendation: str

    def as_row(self, assessment: Assessment) -> dict[str, str | int]:
        pillar = next(p for p in assessment.pillars if p.key == self.item.pillar)
        return {
            "rank": self.rank,
            "key": self.key,
            "best_practice": self.item.id,
            "pillar": pillar.name,
            "question": self.item.question,
            "title": self.item.title,
            "status": self.item.status,
            "risk": self.item.risk or "",
            "effort": self.item.effort or "",
            "owner": self.item.owner or "",
            "roadmap_days": self.bucket,
            "depends_on": " ".join(self.item.depends_on),
            "evidence": " ".join(self.item.evidence),
            "recommendation": self.recommendation,
        }


def sort_key(item: Item) -> tuple:
    return (RISK_RANK[item.risk], EFFORT_RANK[item.effort], PILLARS.index(item.pillar), item.id)


def schedule(gaps: list[Item]) -> dict[str, int]:
    """Return the roadmap bucket for every gap, after pulling dependencies forward."""
    bucket = {item.id: BASE_BUCKET[(item.risk, item.effort)] for item in gaps}
    by_id = {item.id: item for item in gaps}
    changed = True
    # Repeat until stable so a pull travels down a whole dependency chain. Buckets only move earlier and there are
    # three of them, so this ends after a few passes; model.validate already rejects cycles.
    while changed:
        changed = False
        for item in gaps:
            for dep in item.depends_on:
                if dep in by_id and bucket[dep] > bucket[item.id]:
                    bucket[dep] = bucket[item.id]
                    changed = True
    return bucket


def build(assessment: Assessment, figures: dict) -> list[BacklogItem]:
    gaps = sorted((item for item in assessment.items() if item.is_gap), key=sort_key)
    buckets = schedule(gaps)
    width = len(str(len(gaps)))
    return [
        BacklogItem(
            rank=rank,
            key=f"HG-{rank:0{max(width, 2)}d}",
            item=item,
            bucket=buckets[item.id],
            base_bucket=BASE_BUCKET[(item.risk, item.effort)],
            recommendation=fill(item.recommendation or "", figures),
        )
        for rank, item in enumerate(gaps, start=1)
    ]


def roadmap(backlog: list[BacklogItem]) -> dict[int, list[BacklogItem]]:
    """Group backlog items by bucket, dependencies first within a bucket, then by rank."""
    plan: dict[int, list[BacklogItem]] = {}
    for days in BUCKETS:
        chosen = [entry for entry in backlog if entry.bucket == days]
        plan[days] = _dependency_order(chosen)
    return plan


def _dependency_order(entries: list[BacklogItem]) -> list[BacklogItem]:
    remaining = sorted(entries, key=lambda entry: entry.rank)
    ids = {entry.item.id for entry in remaining}
    ordered: list[BacklogItem] = []
    done: set[str] = set()
    while remaining:
        ready = next(
            entry for entry in remaining if all(dep in done or dep not in ids for dep in entry.item.depends_on)
        )
        ordered.append(ready)
        done.add(ready.item.id)
        remaining.remove(ready)
    return ordered
