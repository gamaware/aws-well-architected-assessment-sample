"""Pillar scores, question risks (HRI and MRI) and maturity levels.

Rules (docs/methodology.md and ADR 0002):

- A best practice earns 1 when met, 0.5 when partial and 0 when not met. Not applicable ones are left out.
- A pillar score is the credit earned over the applicable best practices, as a whole percentage.
- A question is a high-risk issue (HRI) when any gap under it is rated high, and a medium-risk issue (MRI) when
  its worst gap is medium. Low-rated gaps are improvement items, not risks, as in the Well-Architected Tool.
"""

from __future__ import annotations

from dataclasses import dataclass

from wa_assess.metrics import round_half_up
from wa_assess.model import Assessment, Pillar

CREDIT = {"met": 1.0, "partial": 0.5, "not_met": 0.0}
MATURITY = ((80, 4, "Optimized"), (60, 3, "Defined"), (40, 2, "Repeatable"), (0, 1, "Initial"))


@dataclass(frozen=True)
class PillarScore:
    key: str
    name: str
    lens: str
    applicable: int
    met: int
    partial: int
    not_met: int
    not_applicable: int
    score_pct: int
    maturity_level: int
    maturity_name: str
    question_risk: dict[str, str]

    @property
    def hri(self) -> int:
        return sum(risk == "high" for risk in self.question_risk.values())

    @property
    def mri(self) -> int:
        return sum(risk == "medium" for risk in self.question_risk.values())

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "lens": self.lens,
            "applicable": self.applicable,
            "met": self.met,
            "partial": self.partial,
            "not_met": self.not_met,
            "not_applicable": self.not_applicable,
            "score_pct": self.score_pct,
            "maturity_level": self.maturity_level,
            "maturity_name": self.maturity_name,
            "hri": self.hri,
            "mri": self.mri,
            "question_risk": self.question_risk,
        }


def maturity(score_pct: int) -> tuple[int, str]:
    return next((level, name) for floor, level, name in MATURITY if score_pct >= floor)


def question_risk(pillar: Pillar, question: str) -> str:
    gaps = {item.risk for item in pillar.items if item.question == question and item.is_gap}
    if "high" in gaps:
        return "high"
    if "medium" in gaps:
        return "medium"
    return "none"


def score_pillar(pillar: Pillar) -> PillarScore:
    counts = {status: sum(item.status == status for item in pillar.items) for status in (*CREDIT, "not_applicable")}
    applicable = len(pillar.items) - counts["not_applicable"]
    credit = sum(CREDIT[item.status] for item in pillar.items if item.status in CREDIT)
    score = round_half_up(100 * credit / applicable, 0) if applicable else 0
    level, name = maturity(score)
    return PillarScore(
        key=pillar.key,
        name=pillar.name,
        lens=pillar.lens,
        applicable=applicable,
        met=counts["met"],
        partial=counts["partial"],
        not_met=counts["not_met"],
        not_applicable=counts["not_applicable"],
        score_pct=score,
        maturity_level=level,
        maturity_name=name,
        question_risk={q: question_risk(pillar, q) for q in pillar.questions},
    )


def summarize(assessment: Assessment) -> dict:
    """Scores per pillar plus totals for the framework and for the DevOps lens."""
    pillars = [score_pillar(pillar) for pillar in assessment.pillars]

    def totals(lens: str) -> dict:
        chosen = [p for p in pillars if p.lens == lens]
        items = [i for p in assessment.pillars if p.lens == lens for i in p.items if i.status in CREDIT]
        credit = sum(CREDIT[i.status] for i in items)
        score = round_half_up(100 * credit / len(items), 0) if items else 0
        gaps = [i for i in items if i.is_gap]
        return {
            "best_practices": len(items),
            "questions": sum(len(p.question_risk) for p in chosen),
            "score_pct": score,
            "hri": sum(p.hri for p in chosen),
            "mri": sum(p.mri for p in chosen),
            "gaps": len(gaps),
            "gaps_by_risk": {risk: sum(i.risk == risk for i in gaps) for risk in ("high", "medium", "low")},
        }

    return {
        "pillars": [p.as_dict() for p in pillars],
        "framework": totals("wellarchitected"),
        "devops": totals("devops"),
    }
