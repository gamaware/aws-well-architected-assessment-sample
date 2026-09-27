# 0001. Record answers as data and generate the report tables from them

## Status

Accepted

## Context

An assessment report quotes the same numbers many times: pillar scores, risk counts, backlog size, delivery
metrics. When someone types the report by hand, a late change to one answer leaves stale numbers elsewhere, and a
reader cannot tell how the assessor reached a score. Clients also want the backlog in a tracker, not only in a PDF.

## Decision

Every answer is a structured entry in `data/synthetic/answers/<pillar>.yaml` with its status, risk, effort, owner,
evidence IDs and dependencies. Figures that come from exports are placeholders (for example `{delivery.rollbacks}`)
filled from the CSV files. Scripts in `scripts/wa_assess/` validate the data and write every table in
`report/REPORT.md` between `BEGIN GENERATED` and `END GENERATED` markers, plus `evidence/backlog.csv` and the other
evidence files. Narrative prose outside the markers stays hand-written and avoids hard-coded numbers.

## Consequences

- One edit to the data updates the scores, backlog, roadmap and report together.
- The backlog imports into a tracker as CSV.
- Hand-written prose must not repeat numbers, which takes some discipline when writing the executive summary.
- The data schema is a small contract that validation enforces; unusual findings must fit it or extend it.

## Compliance

`make check` (part of `make verify` and CI) regenerates every output in memory and fails when a committed file
differs. `tests/test_report.py` fails if a placeholder stays unfilled or the report cites unknown evidence.

## Notes

Alternatives considered: a spreadsheet (hard to review in pull requests, formulas hide the rules) and a template
engine rendering the whole report (prose becomes awkward to edit).
