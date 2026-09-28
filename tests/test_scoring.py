"""Scoring rules on small hand-built pillars, so each rule is checked in isolation."""

from __future__ import annotations

import pytest

from wa_assess import scoring
from wa_assess.model import Item, Pillar


def item(item_id: str, question: str, status: str, risk: str | None = None) -> Item:
    return Item(
        id=item_id,
        pillar="security",
        question=question,
        title=item_id,
        status=status,
        observation="observed",
        evidence=("EV-01",),
        risk=risk,
        effort="S" if risk else None,
        owner="Team" if risk else None,
        recommendation="Fix it" if risk else None,
    )


def pillar(*items: Item) -> Pillar:
    questions = {i.question: i.question for i in items}
    return Pillar(key="security", name="Security", lens="wellarchitected", questions=questions, items=items)


def test_partial_earns_half_and_not_applicable_is_left_out():
    score = scoring.score_pillar(
        pillar(
            item("SEC01-BP01", "SEC01", "met"),
            item("SEC01-BP02", "SEC01", "partial", "low"),
            item("SEC02-BP01", "SEC02", "not_met", "low"),
            item("SEC02-BP02", "SEC02", "not_applicable"),
        )
    )
    assert score.applicable == 3
    assert score.score_pct == 50  # (1 + 0.5 + 0) / 3


def test_question_risk_takes_the_worst_gap_and_ignores_low():
    score = scoring.score_pillar(
        pillar(
            item("SEC01-BP01", "SEC01", "partial", "medium"),
            item("SEC01-BP02", "SEC01", "not_met", "high"),
            item("SEC02-BP01", "SEC02", "partial", "medium"),
            item("SEC02-BP02", "SEC02", "not_met", "low"),
            item("SEC03-BP01", "SEC03", "not_met", "low"),
            item("SEC04-BP01", "SEC04", "met"),
        )
    )
    assert score.question_risk == {"SEC01": "high", "SEC02": "medium", "SEC03": "none", "SEC04": "none"}
    assert (score.hri, score.mri) == (1, 1)


@pytest.mark.parametrize(("pct", "level"), [(0, 1), (39, 1), (40, 2), (59, 2), (60, 3), (79, 3), (80, 4), (100, 4)])
def test_maturity_thresholds(pct, level):
    assert scoring.maturity(pct)[0] == level


def test_score_rounds_half_up():
    # 5 met + 1 partial out of 8 = 68.75 -> 69
    items = [item(f"SEC01-BP0{n}", "SEC01", "met") for n in range(1, 6)]
    items += [item("SEC01-BP06", "SEC01", "partial", "low")]
    items += [item(f"SEC01-BP0{n}", "SEC01", "not_met", "low") for n in (7, 8)]
    assert scoring.score_pillar(pillar(*items)).score_pct == 69


def test_a_pillar_with_nothing_applicable_scores_zero_instead_of_failing():
    score = scoring.score_pillar(pillar(item("SEC01-BP01", "SEC01", "not_applicable")))
    assert (score.applicable, score.score_pct, score.maturity_level) == (0, 0, 1)
