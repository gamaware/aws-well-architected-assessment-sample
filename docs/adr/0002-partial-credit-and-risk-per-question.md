# ADR 0002: Score with partial credit and count risks per question

## Status

Accepted

## Context

The AWS Well-Architected Tool records each best practice as selected or not, and reports high-risk and
medium-risk issues per question. Interviews rarely produce a clean yes or no: a practice is often in place for one
service and missing for another. Readers of the report also need a single number per pillar to track progress
between reviews.

## Decision

- Each best practice is `met` (1 point), `partial` (0.5), `not_met` (0) or `not_applicable` (left out). A pillar
  score is the share of points earned, rounded half up to a whole percentage.
- The assessor rates every gap high, medium or low with a likelihood and impact matrix
  ([methodology](../methodology.md#rating-risk)).
- A question is a high-risk issue when the assessor rates any gap under it high, and a medium-risk issue when its
  worst gap is medium. Low-rated gaps are improvement items, as in the Tool.

## Consequences

- The score shows progress on partly done practices that the Tool's binary model would hide.
- Risk counts are per question, so they read the same way as the Tool's lens review.
- The report's counts can differ from the Tool's for the same workload, because the Tool applies its own rules per
  question and treats unreviewed practices as not selected. The methodology states this, and `make test-live`
  prints both.

## Compliance

`tests/test_scoring.py` covers each rule on hand-built pillars. `tests/reference.py` implements the rules a second
time without the scripts' code, and `tests/test_report.py` checks every pillar row and question risk in the report
against it.

## Notes

The team rejected weighting best practices by AWS's documented risk level: the assessor's rating for this workload
is what drives priority, and mixing two scales confuses readers.
