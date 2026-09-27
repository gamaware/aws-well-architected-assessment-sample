# ADR 0004: Verify offline in CI and keep the Well-Architected Tool round trip manual

## Status

Accepted

## Context

The report must be reproducible by anyone who clones the repository, without an AWS account. At the same time the
best-practice IDs and titles only prove themselves against the AWS Well-Architected Tool, which needs credentials
and creates a resource.

## Decision

- `make verify` runs offline: ruff, the unit tests, the independent recomputation of every report number, and
  `make check`. CI runs the same target with no cloud credentials and no `id-token` permission.
- `make test-live` is manual and uses the maintainer's `dev` profile only. It shows the caller identity and asks
  for confirmation, creates a workload tagged `purpose=portfolio-test`, records the framework answers, prints the
  Tool's risk counts next to the report's, fails if any best-practice title is unknown to the Tool, and deletes the
  workload in an exit trap. It then checks that nothing tagged `purpose=portfolio-test` remains. Output goes to
  `live-output/`, which git ignores.

## Consequences

- Contributors and reviewers never need AWS access.
- The live check covers the framework lens only; DevOps lens titles are checked against the published DevOps
  Guidance by review, not by the live test.
- A title that AWS renames is caught only when the live test is run.

## Compliance

The CI workflow grants only `contents: read` to the verify job. `tests/test_live_offline.py` runs the live
script's matching logic against a fake Tool client in every CI run.

## Notes

Using the Tool's exported JSON as the source of truth was rejected: an export from a real account cannot be
published, and a hand-made one would prove nothing.
