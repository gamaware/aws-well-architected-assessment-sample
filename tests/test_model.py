"""Validation rejects data the scoring rules cannot handle, and reports every problem at once."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from wa_assess.model import AssessmentError, load


def edit(root: Path, pillar: str, change) -> None:
    path = root / "data" / "synthetic" / "answers" / f"{pillar}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def find(data: dict, item_id: str) -> dict:
    return next(entry for entry in data["items"] if entry["id"] == item_id)


def test_committed_data_is_valid(repo_root):
    assessment = load(repo_root / "data" / "synthetic")
    assert len(assessment.pillars) == 7
    assert len({item.id for item in assessment.items()}) == len(assessment.items())


@pytest.mark.parametrize(
    ("pillar", "change", "message"),
    [
        ("security", lambda d: find(d, "SEC02-BP02").update(id="SEC2-BP02"), "not a valid wellarchitected"),
        ("security", lambda d: find(d, "SEC02-BP02").update(id="OPS02-BP02"), "belongs to another pillar"),
        ("security", lambda d: find(d, "SEC02-BP02").update(question="SEC03"), "question should be SEC02"),
        ("devops", lambda d: find(d, "DL.CI.1").update(id="XX.CI.1"), "not a valid devops"),
        ("security", lambda d: find(d, "SEC02-BP02").pop("risk"), "a gap needs a risk"),
        ("security", lambda d: find(d, "SEC02-BP02").pop("recommendation"), "needs an owner and a recommendation"),
        ("security", lambda d: find(d, "SEC01-BP01").update(risk="high"), "only gaps take risk"),
        ("security", lambda d: find(d, "SEC02-BP02").update(status="done"), "unknown status"),
        ("security", lambda d: find(d, "SEC02-BP02").update(risk="critical"), "a gap needs a risk"),
        ("security", lambda d: find(d, "SEC02-BP02").update(effort="XL"), "a gap needs an effort"),
        ("security", lambda d: find(d, "SEC02-BP02").update(evidence=["EV-99"]), "unknown evidence EV-99"),
        ("security", lambda d: find(d, "SEC03-BP02").update(depends_on=["SEC09-BP09"]), "unknown item SEC09-BP09"),
        ("security", lambda d: find(d, "SEC03-BP02").update(depends_on=["SEC01-BP01"]), "already met"),
        ("security", lambda d: find(d, "SEC03-BP02").update(depends_on=["SEC03-BP02"]), "depends on itself"),
        ("security", lambda d: find(d, "SEC02-BP02").update(depends_on=["SEC03-BP02"]), "dependency cycle"),
        ("security", lambda d: d["questions"].update(SEC05="Unanswered question?"), "SEC05 has no answers"),
        ("security", lambda d: d.update(pillar="safety"), "pillar field says 'safety'"),
        ("security", lambda d: find(d, "SEC01-BP01").update(title=None), "title and observation are required"),
    ],
)
def test_validation_rejects_broken_data(data_copy, pillar, change, message):
    edit(data_copy, pillar, change)
    with pytest.raises(AssessmentError, match=message):
        load(data_copy / "data" / "synthetic")


def test_uncited_evidence_is_rejected(data_copy):
    path = data_copy / "data" / "synthetic" / "evidence.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["evidence"].append({"id": "EV-99", "kind": "review", "title": "Never used"})
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(AssessmentError, match="EV-99: evidence is never cited"):
        load(data_copy / "data" / "synthetic")


def test_every_problem_is_reported_together(data_copy):
    edit(data_copy, "security", lambda d: find(d, "SEC02-BP02").update(status="done", evidence=["EV-99"]))
    with pytest.raises(AssessmentError) as raised:
        load(data_copy / "data" / "synthetic")
    assert "unknown status" in str(raised.value)
    assert "unknown evidence" in str(raised.value)


def test_duplicate_evidence_ids_are_rejected(data_copy):
    path = data_copy / "data" / "synthetic" / "evidence.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["evidence"].append(dict(data["evidence"][0]))
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(AssessmentError, match="duplicate evidence ID EV-01"):
        load(data_copy / "data" / "synthetic")


def test_evidence_sources_must_stay_under_exports(data_copy):
    path = data_copy / "data" / "synthetic" / "evidence.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["evidence"][4]["source"] = "data/synthetic/workload.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(AssessmentError, match="must sit under data/synthetic/exports"):
        load(data_copy / "data" / "synthetic")


@pytest.mark.parametrize("field", ["evidence", "depends_on"])
def test_id_lists_reject_a_scalar(data_copy, field):
    edit(data_copy, "security", lambda d: find(d, "SEC02-BP02").update({field: "EV-01"}))
    with pytest.raises(AssessmentError, match=f"SEC02-BP02: {field} must be a list of IDs"):
        load(data_copy / "data" / "synthetic")
