"""Backlog ranking and roadmap scheduling rules."""

from __future__ import annotations

import pytest

from wa_assess import backlog
from wa_assess.model import Item, load


def gap(item_id: str, risk: str, effort: str, pillar: str = "security", depends_on: tuple[str, ...] = ()) -> Item:
    return Item(
        id=item_id,
        pillar=pillar,
        question=item_id[:5],
        title=item_id,
        status="not_met",
        observation="observed",
        evidence=("EV-01",),
        risk=risk,
        effort=effort,
        owner="Team",
        recommendation="Fix it",
        depends_on=depends_on,
    )


def test_rank_is_risk_then_effort_then_pillar_then_id():
    items = [
        gap("SEC02-BP01", "medium", "S"),
        gap("REL01-BP01", "high", "M", pillar="reliability"),
        gap("OPS01-BP01", "high", "M", pillar="operational-excellence"),
        gap("SEC01-BP01", "high", "S"),
        gap("SEC01-BP02", "low", "S"),
    ]
    ordered = [i.id for i in sorted(items, key=backlog.sort_key)]
    assert ordered == ["SEC01-BP01", "OPS01-BP01", "REL01-BP01", "SEC02-BP01", "SEC01-BP02"]


@pytest.mark.parametrize(
    ("risk", "effort", "days"),
    [
        ("high", "S", 30),
        ("high", "M", 30),
        ("high", "L", 60),
        ("medium", "S", 60),
        ("medium", "L", 90),
        ("low", "S", 90),
    ],
)
def test_base_bucket(risk, effort, days):
    assert backlog.schedule([gap("SEC01-BP01", risk, effort)]) == {"SEC01-BP01": days}


def test_dependencies_move_forward_along_the_whole_chain():
    items = [
        gap("SEC01-BP01", "high", "S", depends_on=("SEC02-BP01",)),  # 30 days
        gap("SEC02-BP01", "medium", "S", depends_on=("SEC03-BP01",)),  # 60, pulled to 30
        gap("SEC03-BP01", "low", "S"),  # 90, pulled to 30 through SEC02-BP01
        gap("SEC04-BP01", "low", "M", depends_on=("SEC05-BP01",)),  # 90
        gap("SEC05-BP01", "medium", "S"),  # 60, not moved: the dependant is later
    ]
    assert backlog.schedule(items) == {
        "SEC01-BP01": 30,
        "SEC02-BP01": 30,
        "SEC03-BP01": 30,
        "SEC04-BP01": 90,
        "SEC05-BP01": 60,
    }


def test_an_item_needed_by_several_moves_to_the_earliest_dependant():
    items = [
        gap("SEC01-BP01", "low", "M", depends_on=("SEC03-BP01",)),  # 90
        gap("SEC02-BP01", "high", "M", depends_on=("SEC03-BP01",)),  # 30
        gap("SEC03-BP01", "low", "S"),  # 90, needed by both: moves to 30
    ]
    assert backlog.schedule(items)["SEC03-BP01"] == 30


def test_roadmap_never_schedules_an_item_before_its_dependencies(repo_root):
    assessment = load(repo_root / "data" / "synthetic")
    entries = backlog.build(assessment, figures={})
    by_id = {e.item.id: e for e in entries}
    position = {}
    for days, bucket in backlog.roadmap(entries).items():
        for index, entry in enumerate(bucket):
            position[entry.item.id] = (days, index)
    assert set(position) == set(by_id)
    for entry in entries:
        for dep in entry.item.depends_on:
            assert position[dep] < position[entry.item.id], f"{entry.item.id} is planned before {dep}"


def test_keys_follow_rank(repo_root):
    entries = backlog.build(load(repo_root / "data" / "synthetic"), figures={})
    assert [e.key for e in entries[:3]] == ["HG-01", "HG-02", "HG-03"]
    assert [e.rank for e in entries] == list(range(1, len(entries) + 1))
