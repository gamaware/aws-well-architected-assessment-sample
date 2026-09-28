"""Record the assessment answers in the AWS Well-Architected Tool and compare its risk counts with the report.

Called by scripts/live/wa-tool-roundtrip.sh, which checks the account first and deletes the workload afterwards.
It fails when a best-practice title in data/synthetic does not match a choice in the Tool, which is the check that
the IDs and titles in this repository are the ones AWS publishes. Risk counts are printed side by side, not
asserted: the Tool counts unreviewed best practices as not selected and has its own per-question rules.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

from wa_assess.model import load
from wa_assess.scoring import summarize

FRAMEWORK_PILLARS = {
    "operational-excellence": "operationalExcellence",
    "security": "security",
    "reliability": "reliability",
    "performance-efficiency": "performance",
    "cost-optimization": "costOptimization",
    "sustainability": "sustainability",
}
NONE_OF_THESE = "none of these"


def normalize(title: str) -> str:
    """Compare titles without ID prefixes such as "[DL.CI.1]" or "OPS05-BP01", case or spacing."""
    title = re.sub(r"^\s*(\[[A-Z.0-9]+\]|[A-Z]+\d{2}-BP\d{2}:?)\s*", "", title)
    return " ".join(title.lower().rstrip(".").split())


def answers(client, workload_id: str, lens: str) -> list[dict]:
    found, token = [], None
    while True:
        kwargs = {"WorkloadId": workload_id, "LensAlias": lens, "MaxResults": 50}
        if token:
            kwargs["NextToken"] = token
        page = client.list_answers(**kwargs)
        found += page["AnswerSummaries"]
        token = page.get("NextToken")
        if not token:
            return found


def record(client, workload_id: str, lens: str, items: list) -> list[str]:
    """Select the met best practices per question; return the titles the Tool does not know."""
    # Titles are matched within a pillar: the Tool reuses some, such as "Perform post-incident analysis" in both
    # operational excellence and reliability.
    choices, repeated = {}, set()
    for answer in answers(client, workload_id, lens):
        for choice in answer["Choices"]:
            key = (answer["PillarId"], normalize(choice["Title"]))
            if key in choices and key[1] != NONE_OF_THESE:
                repeated.add(key)
            choices[key] = (answer["QuestionId"], choice["ChoiceId"], answer)

    def key_of(item) -> tuple[str, str]:
        return FRAMEWORK_PILLARS.get(item.pillar, item.pillar), normalize(item.title)

    # A title that is missing, or that appears under two questions of one pillar, cannot be matched safely.
    missing = [f"{item.id} {item.title}" for item in items if key_of(item) not in choices or key_of(item) in repeated]
    selected: dict[str, list[str]] = {}
    for item in items:
        match = choices.get(key_of(item))
        if not match or key_of(item) in repeated:
            continue
        question_id, choice_id, _ = match
        selected.setdefault(question_id, [])
        if item.status == "met":
            selected[question_id].append(choice_id)
    by_question = {answer["QuestionId"]: answer for _, _, answer in choices.values()}
    for question_id, met in selected.items():
        # With nothing met, "None of these" records the question as answered instead of leaving it open.
        choices_here = by_question[question_id]["Choices"]
        none = [c["ChoiceId"] for c in choices_here if normalize(c["Title"]) == NONE_OF_THESE]
        client.update_answer(
            WorkloadId=workload_id,
            LensAlias=lens,
            QuestionId=question_id,
            SelectedChoices=met or none,
            Notes="Fictional Harbor Goods sample answer, recorded by make test-live.",
        )
    return missing


def tool_risks(client, workload_id: str, lens: str) -> dict[str, dict]:
    review = client.get_lens_review(WorkloadId=workload_id, LensAlias=lens)["LensReview"]
    return {p["PillarId"]: p.get("RiskCounts", {}) for p in review["PillarReviewSummaries"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--tag", required=True, help="key=value applied to the workload")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    import boto3  # noqa: PLC0415 - only the live group installs boto3; the offline tests import this module

    assessment = load(Path("data/synthetic"))
    scores = {p["key"]: p for p in summarize(assessment)["pillars"]}
    client = boto3.Session(profile_name=args.profile, region_name=args.region).client("wellarchitected")
    tag_key, tag_value = args.tag.split("=", 1)

    workload_id = client.create_workload(
        WorkloadName=args.name,
        Description="Fictional Harbor Goods sample from aws-well-architected-assessment-sample. Safe to delete.",
        Environment="PREPRODUCTION",
        AwsRegions=[args.region],
        ReviewOwner="portfolio-test",
        Lenses=["wellarchitected"],
        Tags={tag_key: tag_value},
        ClientRequestToken=str(uuid.uuid4()),
    )["WorkloadId"]
    print(f"Created workload {workload_id}")

    framework_items = [i for p in assessment.pillars if p.lens == "wellarchitected" for i in p.items]
    missing = record(client, workload_id, "wellarchitected", framework_items)

    risks = tool_risks(client, workload_id, "wellarchitected")
    rows = []
    for key, pillar_id in FRAMEWORK_PILLARS.items():
        counts = risks.get(pillar_id, {})
        rows.append(
            {
                "pillar": scores[key]["name"],
                "report_hri": scores[key]["hri"],
                "tool_high": counts.get("HIGH", 0),
                "report_mri": scores[key]["mri"],
                "tool_medium": counts.get("MEDIUM", 0),
            }
        )

    args.output.mkdir(exist_ok=True)
    (args.output / "roundtrip.json").write_text(json.dumps({"missing": missing, "risks": rows}, indent=2) + "\n")
    print(f"{'Pillar':<24} {'HRI':>4} {'Tool HIGH':>10} {'MRI':>4} {'Tool MEDIUM':>12}")
    for row in rows:
        print(
            f"{row['pillar']:<24} {row['report_hri']:>4} {row['tool_high']:>10} "
            f"{row['report_mri']:>4} {row['tool_medium']:>12}"
        )
    if missing:
        print("Titles not found in the Tool:", *missing, sep="\n  ", file=sys.stderr)
        return 1
    print(f"All {len(framework_items)} framework best-practice titles match choices in the Tool.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
