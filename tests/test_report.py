"""The report and evidence/ are reproduced from data/synthetic.

Two kinds of proof:

1. Byte-for-byte: regenerating from the data gives exactly the committed files (the same check as `make check`).
2. Independent: the numbers printed in the report are recomputed here straight from the YAML and CSV files, with
   none of the scripts' scoring code, and must agree.
"""

from __future__ import annotations

import csv
import re
import subprocess

import pytest
import yaml

import reference
from wa_assess.__main__ import main, outputs
from wa_assess.model import load
from wa_assess.render import Renderer

ALLOWED_ACCOUNT_IDS = {"111122223333", "444455556666", "123456789012"}


def table_after(text: str, header_start: str) -> list[list[str]]:
    """Rows of the first Markdown table whose header starts with `header_start`."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(header_start))
    rows = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


@pytest.fixture
def report(repo_root) -> str:
    return (repo_root / "report" / "REPORT.md").read_text(encoding="utf-8")


def test_committed_outputs_match_a_fresh_generation(repo_root, capsys):
    """Byte-for-byte: evidence/ and the report's generated blocks are what the data produces today."""
    for relative, content in outputs(repo_root).items():
        assert (repo_root / relative).read_text(encoding="utf-8") == content, f"{relative} is stale"
    assert main(["check", "--root", str(repo_root)]) == 0
    assert "outputs match" in capsys.readouterr().out


def test_check_command_fails_when_the_data_changes(data_copy, repo_root):
    (data_copy / "evidence").mkdir()
    for path in (repo_root / "evidence").iterdir():
        (data_copy / "evidence" / path.name).write_bytes(path.read_bytes())
    assert main(["check", "--root", str(data_copy)]) == 0

    deployments = data_copy / "data" / "synthetic" / "exports" / "deployments.csv"
    with deployments.open("a", encoding="utf-8") as handle:
        handle.write("DEP-999,90,orders-api,12.0,rolled_back,\n")
    assert main(["check", "--root", str(data_copy)]) == 1


@pytest.fixture
def ref(repo_root) -> dict:
    return reference.load(repo_root)


def test_pillar_rows_are_recomputed_independently(ref, report):
    printed = {row[0]: row for row in table_after(report, "| Pillar |") + table_after(report, "| Lens |")}
    for data in ref["answers"].values():
        row = printed[data["name"]]
        pct = reference.percent(data["items"])
        risks = reference.question_risks(data)
        counts = [str(sum(i["status"] == s for i in data["items"])) for s in ("met", "partial", "not_met")]
        expected = [f"{pct}%", reference.maturity(pct), *counts]
        expected += [str(list(risks.values()).count("High")), str(list(risks.values()).count("Medium"))]
        assert row[1:] == expected, data["name"]


def test_question_risk_tables_are_recomputed_independently(ref, report):
    printed = {q: r for q, _, r in re.findall(r"^\| ([A-Z.0-9]+) \| (.+) \| (High|Medium|None) \|$", report, re.M)}
    expected = {q: r for data in ref["answers"].values() for q, r in reference.question_risks(data).items()}
    assert printed == expected


def test_summary_rows_are_recomputed_independently(ref, report):
    summary = dict((row[0], row[1]) for row in table_after(report, "| Measure |"))
    answers = ref["answers"]
    framework = [i for k, d in answers.items() if k != "devops" for i in d["items"]]
    framework_risks = [r for k, d in answers.items() if k != "devops" for r in reference.question_risks(d).values()]
    devops_risks = list(reference.question_risks(answers["devops"]).values())
    gap_items = reference.gaps(ref)
    plan = reference.buckets(gap_items)
    by_risk = [sum(i["risk"] == r for i in gap_items) for r in ("high", "medium", "low")]
    delivery = reference.delivery(ref)
    assert summary == {
        "Well-Architected score (six pillars)": f"{reference.percent(framework)}%",
        "DevOps lens score": f"{reference.percent(answers['devops']['items'])}%",
        "High-risk issues (HRI), framework and DevOps lens": (
            f"{framework_risks.count('High')} and {devops_risks.count('High')}"
        ),
        "Medium-risk issues (MRI), framework and DevOps lens": (
            f"{framework_risks.count('Medium')} and {devops_risks.count('Medium')}"
        ),
        "Best practices reviewed": str(sum(len(d["items"]) for d in answers.values())),
        "Backlog items (high, medium, low)": f"{len(gap_items)} ({by_risk[0]}, {by_risk[1]}, {by_risk[2]})",
        "Items planned for 30, 60 and 90 days": ", ".join(
            str(list(plan.values()).count(days)) for days in (30, 60, 90)
        ),
        "Deployments per week": str(delivery["per_week"]),
        "Change failure rate": f"{delivery['change_failure_rate']}%",
        "Median time to restore service": f"{reference.restore_median(ref)} minutes",
    }


def test_backlog_csv_order_and_roadmap_are_recomputed_independently(ref, repo_root):
    gap_items = reference.gaps(ref)
    plan = reference.buckets(gap_items)
    with (repo_root / "evidence" / "backlog.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["best_practice"] for row in rows] == [i["id"] for i in gap_items]
    for row, item in zip(rows, gap_items, strict=True):
        assert (row["risk"], row["effort"]) == (item["risk"], item["effort"])
        assert int(row["roadmap_days"]) == plan[item["id"]], item["id"]


def test_report_has_no_unfilled_placeholders_and_cites_known_evidence(repo_root, report):
    assert not re.search(r"\{[a-z_]+\.[a-z0-9_]+\}", report)
    known = {e["id"] for e in yaml.safe_load((repo_root / "data/synthetic/evidence.yaml").read_text())["evidence"]}
    assert set(re.findall(r"EV-\d+", report)) <= known


def test_only_documentation_example_account_ids_appear(repo_root):
    # Only files git tracks: gitignored local files (tool caches, live-test output) are never published.
    # /usr/bin/git exists on macOS and the Ubuntu CI runner; an absolute literal keeps ruff's S603/S607 satisfied.
    suffixes = {".md", ".yaml", ".yml", ".csv", ".json", ".sh", ".py", ".toml", ".drawio", ".svg", ".ini", ".cfg"}
    tracked = subprocess.run(
        ["/usr/bin/git", "ls-files", "-z"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.split("\0")
    for name in filter(None, tracked):
        path = repo_root / name
        if path.suffix not in suffixes or not path.is_file():
            continue
        found = set(re.findall(r"(?<!\d)\d{12}(?!\d)", path.read_text(encoding="utf-8", errors="ignore")))
        assert found <= ALLOWED_ACCOUNT_IDS, f"{name}: {found - ALLOWED_ACCOUNT_IDS}"


def test_a_malformed_generated_marker_is_refused(repo_root, report):
    renderer = Renderer(load(repo_root / "data" / "synthetic"), repo_root)
    broken = report.replace("<!-- BEGIN GENERATED: findings:security -->", "<!-- BEGIN GENERATED findings:security -->")
    assert broken != report
    with pytest.raises(ValueError, match="malformed or unpaired"):
        renderer.report(broken)
