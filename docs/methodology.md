# Assessment methodology

This page describes how the assessment in [`report/REPORT.md`](../report/REPORT.md) runs in an engagement and how
this repository reproduces it. The client, Harbor Goods, is fictional.

## What the assessment covers

- **One workload.** The unit of review in the AWS Well-Architected Framework is a workload: the resources and code
  that together deliver business value. Harbor Goods' workload is `storefront-orders`.
- **The six pillars.** Operational excellence, security, reliability, performance efficiency, cost optimization and
  sustainability.
- **The DevOps lens.** The AWS Well-Architected DevOps Guidance organizes practices into five sagas:
  organizational adoption (OA), development lifecycle (DL), quality assurance (QA), automated governance (AG) and
  observability (O). It appears as the "DevOps" lens in the Well-Architected Tool's lens catalog. This sample
  records findings from all five sagas, covering the capabilities most relevant to the workload; a full engagement
  walks through every capability that applies.
- **Best-practice IDs.** Framework IDs follow the `OPS05-BP01` pattern (pillar, question, best practice). DevOps
  Guidance IDs follow the `[DL.CI.1]` pattern (saga, capability, best practice); the data stores them without
  brackets. The titles match the current AWS documentation word for word: `make test-live` checks the framework
  titles against the AWS Well-Architected Tool, and review checks the DevOps Guidance titles.

## How an engagement runs

| Step | What happens | Output |
| --- | --- | --- |
| 1. Kickoff and access | Agree the workload, the interviewees and the questions that matter most. The client grants read-only access for infrastructure inspection (for example the `ReadOnlyAccess` managed policy through an IAM Identity Center permission set). The assessor confirms the access works before the interview. | Scope note, access check |
| 2. Interview | A two-hour session with the workload owner, the platform lead and engineers walks through each best practice in scope. The assessor records answers as said, with the name of the role that gave them. | Interview notes (EV-01 to EV-03) |
| 3. Evidence | The assessor checks each answer against what is running: read-only exports (IAM credential report, deployment history, incident log) and reviews of the pipeline, infrastructure code, monitoring, backups, costs and security findings. Where the evidence disagrees with the interview, the evidence wins and the finding says so. | Evidence register (EV-04 to EV-13) |
| 4. Record in the Well-Architected Tool | The workload is recorded in the Tool in the client's own account: the client enters it with the assessor, or grants the assessor separately scoped Tool write access. The record applies the Well-Architected Framework lens and the DevOps lens, selects the best practices the evidence supports, and adds notes with evidence IDs. The Tool then reports high-risk and medium-risk issues per question. | Tool workload and milestone |
| 5. Rate and plan | Every gap gets a risk rating, an effort estimate, an owner and a recommendation, then the scripts build the backlog and roadmap from fixed rules (below). | Backlog, roadmap |
| 6. Readout | A walkthrough of the findings with the team, agreeing the order of work. The client keeps the report, the backlog file and the Tool record. | Report and PDF |

Infrastructure inspection is read-only. The client records the assessment in the Well-Architected Tool, or grants
separately scoped Tool write access. In this repository synthetic data stands in for steps 2 and 3, and step 4
is optional through `make test-live`.

## Recording answers

Each best practice in scope is one entry in `data/synthetic/answers/<pillar>.yaml`:

| Field | Meaning |
| --- | --- |
| `status` | `met`, `partial`, `not_met` or `not_applicable` |
| `risk` | For gaps only: `high`, `medium` or `low`, rated by the assessor for this workload |
| `effort` | For gaps only: `S` (up to two days), `M` (up to two weeks), `L` (more than two weeks) for one engineer |
| `owner` | The role that should own the fix |
| `evidence` | IDs from `data/synthetic/evidence.yaml` |
| `depends_on` | Other gaps to close first |
| `observation`, `recommendation` | What the assessor saw, and the change that closes the gap |

Observations quote figures from the exports through placeholders such as `{delivery.rollbacks}`, which the scripts
fill from `data/synthetic/exports/`, so the prose cannot drift from the evidence.

### Rating risk

The Well-Architected Tool records a best practice as selected or not; it does not rate a gap for a given workload.
The assessor does, with two questions: how likely the gap leads to an incident or loss in the next year, and how
bad that would be for the business.

| Likelihood / impact | Minor | Significant | Severe |
| --- | --- | --- | --- |
| Likely | Medium | High | High |
| Possible | Low | Medium | High |
| Unlikely | Low | Low | Medium |

## Scoring rules

These rules live in `scripts/wa_assess/scoring.py` and `tests/reference.py` recomputes them independently.

- A best practice earns 1 when met, 0.5 when partial and 0 when not met. Not applicable ones do not count.
- A pillar score is the credit earned over the applicable best practices, rounded half up to a whole percentage.
- The framework and DevOps lens totals pool all their best practices; they are not averages of pillar scores.
- A question is a **high-risk issue (HRI)** when the assessor rates any gap under it high, and a **medium-risk issue
  (MRI)** when its worst gap is medium. Low-rated gaps are improvement items, not risks. This matches how the Tool
  counts risks per question rather than per best practice.
- Maturity levels: 1 Initial (below 40%), 2 Repeatable (40% to 59%), 3 Defined (60% to 79%), 4 Optimized (80% and
  above).

Partial credit is this method's choice, not the Tool's: in the Tool a partial answer is simply not selected. The
Tool's risk counts can therefore differ from the report's where the Tool's own rules for a question differ;
`make test-live` shows both side by side.

## Backlog and roadmap rules

These rules live in `scripts/wa_assess/backlog.py`.

1. Every gap becomes one backlog item.
2. The scripts rank items by risk (high, medium, low), then effort (S, M, L), then pillar order, then best-practice ID.
   Keys `HG-01`, `HG-02` and so on follow the rank.
3. Each item gets a starting bucket:

   | Risk | S | M | L |
   | --- | --- | --- | --- |
   | High | 30 days | 30 days | 60 days |
   | Medium | 60 days | 60 days | 90 days |
   | Low | 90 days | 90 days | 90 days |

4. An item that other items depend on moves forward to the earliest bucket among the items that need it, so no
   plan waits on work scheduled later. Within a bucket, dependencies come first, then rank order.

The roadmap is a starting proposal for the readout. The team adjusts it for capacity and business events, and the
backlog file (`evidence/backlog.csv`) imports into most trackers.

## What the repository reproduces

| Engagement artifact | In this repository |
| --- | --- |
| Interview notes and read-only exports | `data/synthetic/` (fictional) |
| Tool workload and answers | `make test-live` round trip in a test account |
| Scores, backlog and roadmap | `evidence/`, produced by `make evidence` |
| Report | `report/REPORT.md` and `report/REPORT.pdf` |
| Proof the numbers follow from the data | `make verify` (ruff, tests and `make check`) |
