"""The live round trip's matching logic, run against a fake Well-Architected Tool client (no AWS calls)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from wa_assess.model import Item

spec = importlib.util.spec_from_file_location(
    "roundtrip", Path(__file__).resolve().parent.parent / "scripts" / "live" / "wa_tool_roundtrip.py"
)
roundtrip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(roundtrip)


class FakeTool:
    def __init__(self):
        self.updates = []

    def list_answers(self, **_):
        choices = [
            {"ChoiceId": "ops_version_control", "Title": "OPS05-BP01 Use version control"},
            {"ChoiceId": "ops_test", "Title": "Test and validate changes."},
            {"ChoiceId": "ops_none", "Title": "None of these"},
        ]
        rollback = [
            {"ChoiceId": "ops_plan", "Title": "Plan for unsuccessful changes"},
            {"ChoiceId": "ops6_none", "Title": "None of these"},
        ]
        return {
            "AnswerSummaries": [
                {"PillarId": "operationalExcellence", "QuestionId": "dev-integ", "Choices": choices},
                {"PillarId": "operationalExcellence", "QuestionId": "mit-deploy-risks", "Choices": rollback},
            ]
        }

    def update_answer(self, **kwargs):
        self.updates.append(kwargs)


def item(item_id, title, status, pillar="operational-excellence"):
    return Item(
        id=item_id,
        pillar=pillar,
        question=item_id[:5],
        title=title,
        status=status,
        observation="o",
        evidence=("EV-01",),
    )


def test_titles_match_despite_prefixes_case_and_punctuation():
    assert roundtrip.normalize("[DL.CI.1] Integrate code changes.") == "integrate code changes"
    assert roundtrip.normalize("OPS05-BP01 Use Version Control") == "use version control"


def test_met_items_are_selected_and_unmet_questions_get_none_of_these():
    tool = FakeTool()
    missing = roundtrip.record(
        tool,
        "wl-1",
        "wellarchitected",
        [
            item("OPS05-BP01", "Use version control", "met"),
            item("OPS05-BP02", "Test and validate changes", "partial"),
            item("OPS06-BP01", "Plan for unsuccessful changes", "not_met"),
            item("OPS09-BP09", "A title AWS never published", "met"),
        ],
    )
    assert missing == ["OPS09-BP09 A title AWS never published"]
    selected = {u["QuestionId"]: u["SelectedChoices"] for u in tool.updates}
    assert selected == {"dev-integ": ["ops_version_control"], "mit-deploy-risks": ["ops6_none"]}


def test_a_title_listed_under_two_questions_is_reported_not_guessed():
    class Twice(FakeTool):
        def list_answers(self, **kwargs):
            page = super().list_answers(**kwargs)
            page["AnswerSummaries"][1]["Choices"].append({"ChoiceId": "dup", "Title": "Use version control"})
            return page

    tool = Twice()
    missing = roundtrip.record(tool, "wl-1", "wellarchitected", [item("OPS05-BP01", "Use version control", "met")])
    assert missing == ["OPS05-BP01 Use version control"]
    assert tool.updates == []


def test_a_title_reused_by_another_pillar_matches_within_its_own_pillar():
    class OtherPillar(FakeTool):
        def list_answers(self, **kwargs):
            page = super().list_answers(**kwargs)
            page["AnswerSummaries"].append(
                {
                    "PillarId": "reliability",
                    "QuestionId": "rel-learn",
                    "Choices": [{"ChoiceId": "rel_vc", "Title": "Use version control"}],
                }
            )
            return page

    tool = OtherPillar()
    missing = roundtrip.record(
        tool,
        "wl-1",
        "wellarchitected",
        [
            item("OPS05-BP01", "Use version control", "met"),
            item("REL12-BP01", "Use version control", "not_met", pillar="reliability"),
        ],
    )
    assert missing == []
    selected = {u["QuestionId"]: u["SelectedChoices"] for u in tool.updates}
    assert selected == {"dev-integ": ["ops_version_control"], "rel-learn": []}
